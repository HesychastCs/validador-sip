import streamlit as st
import zipfile
import os
import mimetypes

from openpyxl.styles.builtins import total
from sqlalchemy.testing.util import total_size


def validate_sip(uploaded_file):
    errors = []

    header = uploaded_file.read(4)
    uploaded_file.seek(0)

    if header != b'PK\x03\x04':
        errors.append("Firma de archivo inválida: No parece ser un contenedor .sip o .zip válido.")

    try:
        with zipfile.ZipFile(uploaded_file) as sip:
            bad_file = sip.testzip()
            if bad_file:
                errors.append(f"Archivo corrupto: {bad_file}")

            total_size = sum(f.file_size for f in sip.infolist())
            if total_size > 100 * 1024 * 1024:
                errors.append("EL archivo descomprimido es demasiado grande")

            internal_files = sip.namelist()
            if not any("Model" in name for name in internal_files):
                errors.append("No se encontró la estructura 'Model' dentro del archivo")

    except zipfile.BadZipFile:
        errors.append("EL archivo está mal formado o no es un SIP")
    except Exception as e:
        errors.append(f"Error insperado: {str(e)}")

    return errors

st.set_page_config(page_title="¿está buena esta wea?", page_icon=":dolphin:")

st.title("🛡️ Validador de Modelos Powersim (.sip)")
st.markdown("""
Sube tu archivo para verificar su **integridad**, **firma binaria** y **estructura interna** antes de procesarlo.
""")

uploaded_file = st.file_uploader("Elige un archivo .sip", type=["sip", "zip"])

if uploaded_file is not None:
    st.info(f"Analizando: **{uploaded_file.name}**")

    # Ejecutar validación
    lista_errores = validate_sip(uploaded_file)

    if not lista_errores:
        st.success("✅ ¡Archivo válido! La firma es correcta y la estructura de Powersim es íntegra.")
        st.balloons()

        # Mostrar detalles del archivo
        with st.expander("Ver detalles técnicos"):
            st.write(f"Tamaño: {uploaded_file.size / 1024:.2f} KB")
            st.write(f"Tipo MIME: {uploaded_file.type}")
    else:
        st.error("❌ El archivo no superó las pruebas de seguridad:")
        for err in lista_errores:
            st.warning(err)