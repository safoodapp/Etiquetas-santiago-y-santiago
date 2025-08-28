import streamlit as st
from st_gsheets_connection import GSheetsConnection

st.set_page_config(page_title="Test GSheets")

try:
    conn: GSheetsConnection = st.connection("gsheets", type=GSheetsConnection)
    st.write("✅ Conexión creada")
    df = conn.read(worksheet="datos")
    st.dataframe(df.head())
except Exception as e:
    st.error(f"❌ Error: {e}")
