# Commit for reinstall dependencies
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from docxtpl import DocxTemplate
import base64
import os
import locale
from streamlit_gsheets import GSheetsConnection

# --------------------------
# Config regional (opcional)
# --------------------------
try:
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'es_ES')
    except:
        pass

# --------------------------
# Plantillas y reglas (nombres EXACTOS de tus .docx)
# --------------------------
PLANTILLAS = {
    "pescado_fresco": "FT PESCADOS",
    "moluscos": "FT PULPO",
    "crustaceos": "FT CRUSTACEO",
    "tintorera": "FT TINTORERA",
}

KW_MOLUSCOS   = ["pulpo", "calamar", "pota", "sepia"]
KW_CRUSTACEOS = ["gamba", "gambón", "gambon", "langostino", "camarón", "camaron",
                 "cigala", "carabinero", "bogavante", "langosta"]
KW_TINTORERA  = ["tintorera", "descongelad"]  # cubre 'descongelado/a/os/as'

def resolver_plantilla(denominacion: str, plantilla_excel: str | None = None) -> str:
    """1) Si la fila trae 'plantilla', manda esa. 2) Si no, reglas por keywords.
       3) Por defecto, FT PESCADOS."""
    if plantilla_excel and str(plantilla_excel).strip():
        return str(plantilla_excel).strip()
    d = (denominacion or "").lower()
    if any(k in d for k in KW_TINTORERA):
        return PLANTILLAS["tintorera"]
    if any(k in d for k in KW_MOLUSCOS):
        return PLANTILLAS["moluscos"]
    if any(k in d for k in KW_CRUSTACEOS):
        return PLANTILLAS["crustaceos"]
    return PLANTILLAS["pescado_fresco"]

# --------------------------
# Conexión a Google Sheets
# --------------------------
from st_gsheets_connection import GSheetsConnection

st.set_page_config(page_title="Etiquetas de Santiago y Santiago", layout="centered")

try:
    conn: GSheetsConnection = st.connection("gsheets", type=GSheetsConnection)
    SPREADSHEET_URL = st.secrets["connections"]["gsheets"]["spreadsheet"]
    WORKSHEET_NAME  = st.secrets["connections"]["gsheets"].get("worksheet", "Datos")
except Exception:
    st.error("No se pudo crear la conexión a Google Sheets. Revisa los *Secrets*.")
    st.stop()

COLUMNAS = [
    "denominacion_comercial",
    "nombre_cientifico",
    "ingredientes",
    "forma_capturado",
    "zona_captura",
    "pais_origen",
    "arte_pesca",
    # Si algún día quieres fijar plantilla desde la base:
    # "plantilla",
]

@st.cache_data(ttl=20)
def leer_df_gs() -> pd.DataFrame:
    df_gs = conn.read(spreadsheet=SPREADSHEET_URL, worksheet=WORKSHEET_NAME)
    if df_gs is None or df_gs.empty:
        df_gs = pd.DataFrame({c: [] for c in COLUMNAS})
        conn.update(spreadsheet=SPREADSHEET_URL, worksheet=WORKSHEET_NAME, data=df_gs)
    else:
        df_gs.columns = [str(c).strip() for c in df_gs.columns]
        for c in COLUMNAS:
            if c not in df_gs.columns:
                df_gs[c] = ""
        df_gs = df_gs[COLUMNAS].fillna("").astype(str)
    return df_gs

def guardar_df_gs(df_gs: pd.DataFrame):
    conn.update(spreadsheet=SPREADSHEET_URL, worksheet=WORKSHEET_NAME, data=df_gs)
    leer_df_gs.clear()

def opciones_columna(df: pd.DataFrame, col: str):
    try:
        lista = sorted([str(x) for x in df[col].dropna().unique() if str(x).strip()])
        return ["Selecciona una opción"] + lista
    except Exception:
        return ["Selecciona una opción"]

# --------------------------
# Estado de navegación
# --------------------------
if "mostrar_formulario" not in st.session_state:
    st.session_state.mostrar_formulario = False

# --------------------------
# PORTADA + AÑADIR INFORMACIÓN (GS)
# --------------------------
if not st.session_state.mostrar_formulario:
    st.markdown("<h1 style='text-align:center;'>Etiquetas de Santiago y Santiago</h1>", unsafe_allow_html=True)
    if st.button("➕ Nueva etiqueta"):
        st.session_state.mostrar_formulario = True

    st.markdown("## Añadir información")

    opciones = [
        "denominacion_comercial",  # mostrará 3 inputs
        "forma_capturado",
        "zona_captura",
        "pais_origen",
        "arte_pesca",
    ]

    campo_elegido = st.selectbox(
        "Elegir campo", opciones, index=0,
        format_func=lambda x: x.replace("_", " ").capitalize()
    )

    with st.form("form_add_info", clear_on_submit=True):
        if campo_elegido == "denominacion_comercial":
            den = st.text_input("Denominación comercial")
            nom = st.text_input("Nombre científico")
            ing = st.text_area("Ingredientes", height=110)
        else:
            valor = st.text_area(campo_elegido.replace("_", " ").capitalize(), height=110)

        submitted = st.form_submit_button("Guardar")

        if submitted:
            df_gs = leer_df_gs()
            nueva = {c: "" for c in COLUMNAS}

            if campo_elegido == "denominacion_comercial":
                if not den.strip() or not nom.strip() or not ing.strip():
                    st.warning("Completa denominación comercial, nombre científico e ingredientes.")
                    st.stop()
                nueva["denominacion_comercial"] = den.strip()
                nueva["nombre_cientifico"]     = nom.strip()
                nueva["ingredientes"]          = ing.strip()
            else:
                nueva[campo_elegido] = (valor or "").strip()

            df_gs = pd.concat([df_gs, pd.DataFrame([nueva])], ignore_index=True)
            try:
                guardar_df_gs(df_gs)
                st.success("Información guardada correctamente en Google Sheets ✅")
            except Exception as e:
                st.error("No se pudo guardar en Google Sheets. Revisa permisos y Secrets.")
                st.exception(e)

    st.stop()  # FIN portada

# --------------------------
# FORMULARIO: Generar etiqueta (lee de Google Sheets)
# --------------------------
df = leer_df_gs()

st.header("🧾 Crear nueva etiqueta")

productos = opciones_columna(df, "denominacion_comercial")
formas    = opciones_columna(df, "forma_capturado")
zonas     = opciones_columna(df, "zona_captura")
paises    = opciones_columna(df, "pais_origen")
artes     = opciones_columna(df, "arte_pesca")

producto = st.selectbox("Producto", productos)

if producto != "Selecciona una opción" and (df["denominacion_comercial"] == producto).any():
    fila = df[df["denominacion_comercial"] == producto].iloc[0]
    nombre_cientifico = fila.get("nombre_cientifico", "")
    ingredientes      = fila.get("ingredientes", "")
    plantilla_nombre  = resolver_plantilla(
        denominacion=producto,
        plantilla_excel=fila.get("plantilla", "")
    )
else:
    nombre_cientifico = ""
    ingredientes      = ""
    plantilla_nombre  = PLANTILLAS["pescado_fresco"]

st.text_input("Nombre científico", value=nombre_cientifico, disabled=True)
st.text_area("Ingredientes", value=ingredientes, disabled=True)

forma = st.radio("Forma de capturado", formas, horizontal=True)
zona  = st.selectbox("Zona de captura", zonas)
pais  = st.selectbox("País de origen", paises)
arte  = st.selectbox("Arte de pesca", artes)

lote = st.text_input("Lote")

usar_fecha_descongelacion = st.checkbox("¿Indicar fecha de descongelación?")
fecha_descongelacion = None
fecha_caducidad = None

if usar_fecha_descongelacion:
    fecha_descongelacion = st.date_input("Fecha de descongelación", format="DD/MM/YYYY")
    fecha_caducidad = fecha_descongelacion + timedelta(days=3)
    st.text_input("Fecha de caducidad", value=fecha_caducidad.strftime("%d/%m/%Y"), disabled=True)
else:
    fecha_caducidad = st.date_input("Fecha de caducidad (manual)", format="DD/MM/YYYY")

if st.button("✅ Generar etiqueta"):
    campos = {
        "denominacion_comercial": producto,
        "nombre_cientifico": nombre_cientifico,
        "ingredientes": ingredientes,
        "forma_captura": forma,      # compatibilidad 1
        "forma_capturado": forma,    # compatibilidad 2
        "zona_captura": zona,
        "pais_origen": pais,
        "arte_pesca": arte,
        "lote": lote,
        "fecha_descongelacion": fecha_descongelacion.strftime("%d/%m/%Y") if fecha_descongelacion else "",
        "fecha_caducidad": fecha_caducidad.strftime("%d/%m/%Y") if fecha_caducidad else ""
    }

    oblig = {
        "Producto": producto,
        "Forma de captura": forma,
        "Zona de captura": zona,
        "País de origen": pais,
        "Arte de pesca": arte,
        "Lote": lote
    }
    faltan = [k for k, v in oblig.items() if not v or v == "Selecciona una opción"]
    if faltan:
        st.warning(f"Debes completar todos los campos obligatorios: {', '.join(faltan)}")
        st.stop()

    plantilla_path = f"{plantilla_nombre}.docx"
    if not os.path.exists(plantilla_path):
        st.error(f"No se encontró la plantilla: {plantilla_path}")
    else:
        doc = DocxTemplate(plantilla_path)
        doc.render(campos)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_docx = f"ETIQUETA_{producto.replace(' ', '_')}_{timestamp}.docx"
        doc.save(output_docx)

        with open(output_docx, "rb") as file:
            b64_docx = base64.b64encode(file.read()).decode()
            st.markdown(
                f'<a href="data:application/octet-stream;base64,{b64_docx}" download="{output_docx}">📥 Descargar etiqueta Word</a>',
                unsafe_allow_html=True
            )

        st.info("Si necesitas el archivo en PDF, abre el Word descargado y guárdalo como PDF desde Word o Google Docs.")




