import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from docxtpl import DocxTemplate
import os
import locale

# Configurar idioma del calendario (opcional)
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES')
    except:
        pass

# Configurar página
st.set_page_config(page_title="Etiquetas de Santiago y Santiago", layout="centered")

# Mostrar portada
if "mostrar_formulario" not in st.session_state:
    st.session_state.mostrar_formulario = False

if not st.session_state.mostrar_formulario:
    st.markdown("<h1 style='text-align:center;'>Etiquetas de Santiago y Santiago</h1>", unsafe_allow_html=True)
    if st.button("➕ Nueva etiqueta"):
        st.session_state.mostrar_formulario = True
    st.stop()

# Cargar datos desde Google Sheets (o archivo Excel)
URL_SHEETS = "https://docs.google.com/spreadsheets/d/1M-1zM8pxosv75N5gCtWaPkE1beQBOaMD/export?format=csv&gid=707739207"

try:
    df = pd.read_csv(URL_SHEETS)
except Exception:
    try:
        df = pd.read_excel("ETIQUETA.xlsx", sheet_name="Santiago y Santiago")
    except Exception as e:
        st.error(f"Error al cargar la base de datos: {e}")
        st.stop()

# Preparar opciones para desplegables
def opciones_columna(col):
    try:
        lista = sorted([str(x).strip() for x in df[col].dropna().unique() if str(x).strip()])
        return ["Selecciona una opción"] + lista
    except:
        return ["Selecciona una opción"]

productos = opciones_columna("denominacion_comercial")
formas = opciones_columna("forma_capturado")
zonas = opciones_columna("zona_captura")
paises = opciones_columna("pais_origen")
artes = opciones_columna("arte_pesca")

# Formulario principal
st.header("🧾 Crear nueva etiqueta")

producto = st.selectbox("Producto", productos)

if producto != "Selecciona una opción":
    fila = df[df["denominacion_comercial"] == producto].iloc[0]
    nombre_cientifico = fila.get("nombre_cientifico", "")
    ingredientes = fila.get("ingredientes", "")
    plantilla_nombre = str(fila.get("plantilla", "plantilla_etiqueta")).strip()
else:
    nombre_cientifico = ""
    ingredientes = ""
    plantilla_nombre = "plantilla_etiqueta"

st.text_input("Nombre científico", value=nombre_cientifico, disabled=True)
st.text_area("Ingredientes", value=ingredientes, disabled=True)

forma = st.radio("Forma de capturado / producción", formas, horizontal=True)

# Lógica según método de producción (Acuicultura vs. Capturado)
es_acuicultura = "acui" in (forma or "").lower() or "cría" in (forma or "").lower()

if es_acuicultura:
    zona = ""
    arte = ""
    st.info("Producto de ACUICULTURA: no se requiere Zona FAO ni Arte de pesca.")
else:
    zona = st.selectbox("Zona de captura", zonas)
    arte = st.selectbox("Arte de pesca", artes)

pais = st.selectbox("País de origen", paises)
lote = st.text_input("Lote")

# -------------------------------------------
# GESTIÓN DE FECHAS (CONGELACIÓN / DESCONGELACIÓN)
# -------------------------------------------
col_f1, col_f2 = st.columns(2)

with col_f1:
    usar_fecha_congelacion = st.checkbox("¿Indicar fecha de congelación?")
    fecha_congelacion = None
    if usar_fecha_congelacion:
        fecha_congelacion = st.date_input("Fecha de congelación", format="DD/MM/YYYY")

with col_f2:
    usar_fecha_descongelacion = st.checkbox("¿Indicar fecha de descongelación?")
    fecha_descongelacion = None
    if usar_fecha_descongelacion:
        fecha_descongelacion = st.date_input("Fecha de descongelación", format="DD/MM/YYYY")

if usar_fecha_descongelacion and fecha_descongelacion:
    fecha_caducidad = fecha_descongelacion + timedelta(days=3)
    st.text_input("Fecha de caducidad (+3 días)", value=fecha_caducidad.strftime("%d/%m/%Y"), disabled=True)
else:
    fecha_caducidad = st.date_input("Fecha de caducidad", format="DD/MM/YYYY")

# -------------------------------------------
# BOTÓN DE GENERAR DOCUMENTO
# -------------------------------------------
if st.button("✅ Generar etiqueta"):
    campos = {
        "denominacion_comercial": producto,
        "nombre_cientifico": nombre_cientifico,
        "ingredientes": ingredientes,
        "forma_captura": forma,
        "zona_captura": zona,
        "pais_origen": pais,
        "arte_pesca": arte,
        "lote": lote,
        "fecha_congelacion": fecha_congelacion.strftime("%d/%m/%Y") if fecha_congelacion else "",
        "fecha_descongelacion": fecha_descongelacion.strftime("%d/%m/%Y") if fecha_descongelacion else "",
        "fecha_caducidad": fecha_caducidad.strftime("%d/%m/%Y") if fecha_caducidad else ""
    }

    # Validación de campos obligatorios
    campos_obligatorios = {
        "Producto": producto,
        "Forma de captura": forma,
        "País de origen": pais,
        "Lote": lote
    }

    if not es_acuicultura:
        campos_obligatorios["Zona de captura"] = zona
        campos_obligatorios["Arte de pesca"] = arte

    faltan = [k for k, v in campos_obligatorios.items() if not v or v == "Selecciona una opción"]

    if faltan:
        st.warning(f"Debes completar todos los campos obligatorios: {', '.join(faltan)}")
        st.stop()

    plantilla_path = f"{plantilla_nombre}.docx"
    if not os.path.exists(plantilla_path):
        st.error(f"No se encontró la plantilla de Word: {plantilla_path}")
    else:
        doc = DocxTemplate(plantilla_path)
        doc.render(campos)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_prod = (producto or "ETIQUETA").replace(" ", "_")
        output_docx = f"ETIQUETA_{safe_prod}_{timestamp}.docx"
        doc.save(output_docx)

        with open(output_docx, "rb") as file:
            st.download_button(
                label="📥 Descargar etiqueta Word",
                data=file.read(),
                file_name=output_docx,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )

        st.info("Si necesitas el archivo en PDF, abre el Word descargado y guárdalo como PDF.")