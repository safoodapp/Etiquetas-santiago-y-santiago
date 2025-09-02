import streamlit as st
import pandas as pd
from datetime import datetime, timedelta, date
from docxtpl import DocxTemplate
import os
import locale

# -----------------------------
# Configuración
# -----------------------------
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except Exception:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES')
    except Exception:
        pass

st.set_page_config(page_title="Etiquetas de Santiago y Santiago", layout="centered")

# -----------------------------
# Portada
# -----------------------------
if "mostrar_formulario" not in st.session_state:
    st.session_state.mostrar_formulario = False

if not st.session_state.mostrar_formulario:
    st.markdown("<h1 style='text-align:center;'>Etiquetas de Santiago y Santiago</h1>", unsafe_allow_html=True)
    if st.button("➕ Nueva etiqueta"):
        st.session_state.mostrar_formulario = True
    st.stop()

# -----------------------------
# Carga de datos
# -----------------------------
EXCEL_PATH = "ETIQUETA.xlsx"
SHEET_NAME = "Santiago y Santiago"

try:
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)
except Exception as e:
    st.error(f"Error al cargar el archivo {EXCEL_PATH}: {e}")
    st.stop()

# -----------------------------
# Utilidades
# -----------------------------

def opciones_columna(col: str):
    try:
        serie = df[col].dropna()
        vals = sorted({str(x).strip() for x in serie if str(x).strip()})
        return ["Selecciona una opción"] + list(vals)
    except Exception:
        return ["Selecciona una opción"]

# -----------------------------
# Opciones desde Excel
# -----------------------------
productos = opciones_columna("denominacion_comercial")
formas = opciones_columna("forma_capturado")
zonas = opciones_columna("zona_captura")
paises = opciones_columna("pais_origen")
artes = opciones_columna("arte_pesca")

# -----------------------------
# Formulario
# -----------------------------
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

# Forma de producción / captura
forma = st.radio("Forma de capturado", formas, horizontal=True, index=0)

# Detectar acuicultura (de cría)
forma_lower = (forma or "").lower()
es_de_cria = any(p in forma_lower for p in ["cría", "de cría", "acuicultura", "de cultivo", "piscifactor"]) and forma != "Selecciona una opción"

# Campos condicionales: si es de cría, NO se muestran zona de captura ni arte de pesca
if not es_de_cria:
    zona = st.selectbox("Zona de captura", zonas)
    arte = st.selectbox("Arte de pesca", artes)
else:
    zona = ""
    arte = ""

pais = st.selectbox("País de origen", paises)

lote = st.text_input("Lote")

usar_fecha_descongelacion = st.checkbox("¿Indicar fecha de descongelación?")
fecha_descongelacion: date | None = None
fecha_caducidad: date | None = None

if usar_fecha_descongelacion:
    fecha_descongelacion = st.date_input("Fecha de descongelación", value=date.today())
    fecha_caducidad = fecha_descongelacion + timedelta(days=3)
    st.text_input("Fecha de caducidad", value=fecha_caducidad.strftime("%d/%m/%Y"), disabled=True)
else:
    fecha_caducidad = st.date_input("Fecha de caducidad (manual)", value=date.today())

# -----------------------------
# Generar
# -----------------------------
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
        "fecha_descongelacion": fecha_descongelacion.strftime("%d/%m/%Y") if fecha_descongelacion else "",
        "fecha_caducidad": fecha_caducidad.strftime("%d/%m/%Y") if fecha_caducidad else "",
        "metodo_produccion": "Acuicultura" if es_de_cria else "Pesca extractiva",
    }

    # Validación de obligatorios: si es de cría, NO exigimos zona ni arte
    obligatorios_comunes = {
        "Producto": producto,
        "Forma de captura": forma,
        "País de origen": pais,
        "Lote": lote,
    }

    obligatorios_mar = {} if es_de_cria else {
        "Zona de captura": zona,
        "Arte de pesca": arte,
    }

    faltan = [k for k, v in {**obligatorios_comunes, **obligatorios_mar}.items() if not v or v == "Selecciona una opción"]
    if faltan:
        st.warning(f"Debes completar todos los campos obligatorios: {', '.join(faltan)}")
        st.stop()

    plantilla_path = f"{plantilla_nombre}.docx"
    if not os.path.exists(plantilla_path):
        st.error(f"No se encontró la plantilla: {plantilla_path}")
        st.stop()

    try:
        doc = DocxTemplate(plantilla_path)
        doc.render(campos)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_prod = (producto or "ETIQUETA").replace(" ", "_")
        output_docx = f"ETIQUETA_{safe_prod}_{timestamp}.docx"
        doc.save(output_docx)

        with open(output_docx, "rb") as f:
            st.download_button(
                label="📥 Descargar etiqueta (Word)",
                data=f.read(),
                file_name=output_docx,
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        st.info("Si necesitas el archivo en PDF, abre el Word descargado y guárdalo como PDF.")
    except Exception as e:
        st.error(f"No se pudo generar la etiqueta: {e}")
