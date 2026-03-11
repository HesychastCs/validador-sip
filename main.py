import streamlit as st
import zipfile
import io


def validate_sip(uploaded_file):
    """
    Validador multiformato para archivos .sip de Powersim.
    Soporta: ZIP (Moderno), SEBASTIAN (Legacy) y OLE Compound (Binary).
    """
    errors = []

    # 1. Leer muestra del encabezado (Magic Numbers)
    header_sample = uploaded_file.read(32)
    uploaded_file.seek(0)  # Resetear puntero para futuras lecturas

    # --- CASO 1: Formato Moderno (ZIP) ---
    if header_sample.startswith(b'PK'):
        try:
            with zipfile.ZipFile(uploaded_file) as z:
                # Verificación de integridad física (CRC)
                bad_file = z.testzip()
                if bad_file:
                    errors.append(f"Falla de integridad CRC en: {bad_file}")

                # Verificación de identidad (¿Es realmente Powersim?)
                if not any("Model" in n or "Content" in n for n in z.namelist()):
                    errors.append("Contenedor ZIP válido, pero no se reconoce la estructura de Powersim.")
        except zipfile.BadZipFile:
            errors.append("Firma PK detectada, pero el archivo está truncado o corrupto.")

    # --- CASO 2: Formato Powersim 2005 (Legacy 'SEBASTIAN') ---
    elif header_sample.startswith(b'SEBASTIAN'):
        content = uploaded_file.read().decode('latin-1', errors='ignore')
        uploaded_file.seek(0)

        # El archivo que subiste muestra que debe contener estas palabras clave
        if "Powersim" not in content or "FORM" not in content:
            errors.append("Encabezado 'SEBASTIAN' correcto, pero faltan bloques de datos (FORM/Powersim).")

    # --- CASO 3: Formato OLE Compound (Firma \xd0\xcf\x11\xe0...) ---
    elif header_sample.startswith(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1'):
        # Es un binario complejo tipo MS-Docfile usado por versiones antiguas
        content = uploaded_file.read().decode('latin-1', errors='ignore')
        uploaded_file.seek(0)

        if "Powersim" not in content:
            errors.append("Firma binaria OLE detectada, pero no contiene metadatos de Powersim.")

    # --- CASO 4: Firma Desconocida ---
    else:
        # Mostramos los bytes para facilitar el debug si aparece otro formato
        hex_header = header_sample[:8].hex(' ').upper()
        errors.append(f"Firma no reconocida: {hex_header}. El sistema no acepta este tipo de archivo.")

    # --- VALIDACIÓN DE SEGURIDAD: TAMAÑO ---
    # Límite estricto de 100 KB definido para el proyecto
    if uploaded_file.size > 100 * 1024:
        errors.append(
            f"Riesgo de seguridad: El archivo ({uploaded_file.size / 1024:.1f} KB) excede el límite de 100 KB.")

    return errors


# --- INTERFAZ DE USUARIO (Streamlit) ---
st.set_page_config(page_title="Security Validator", page_icon="🛡️", layout="centered")

st.title("🛡️ Validador de Modelos Powersim (.sip)")
st.write("Herramienta de validación de integridad y seguridad para archivos de simulación.")

uploaded_file = st.file_uploader("Arrastra tu archivo .sip aquí", type=["sip", "zip"])

if uploaded_file is not None:
    st.divider()
    with st.status("Analizando estructura binaria...", expanded=True) as status:
        lista_errores = validate_sip(uploaded_file)

        if not lista_errores:
            status.update(label="Análisis completado: Archivo Seguro", state="complete", expanded=False)
            st.success(f"✅ **{uploaded_file.name}** es un modelo válido e íntegro.")
            st.balloons()

            # Mostrar metadatos detectados
            with st.expander("Ver Detalles de la Firma"):
                header = uploaded_file.read(8)
                uploaded_file.seek(0)
                if header.startswith(b'PK'):
                    tipo = "ZIP / SIP Moderno"
                elif header.startswith(b'SEB'):
                    tipo = "Powersim Legacy (SEBASTIAN)"
                elif header.startswith(b'\xd0\xcf'):
                    tipo = "Microsoft OLE / Powersim Antiguo"
                else:
                    tipo = "Desconocido"

                st.write(f"**Formato detectado:** {tipo}")
                st.write(f"**Peso real:** {uploaded_file.size / 1024:.2f} KB")
        else:
            status.update(label="Análisis completado: Se encontraron riesgos", state="error", expanded=True)
            st.error("El archivo ha sido rechazado por los siguientes motivos:")
            for e in lista_errores:
                st.warning(e)

st.sidebar.info("""
**Reglas de validación:**
1. Firma binaria conocida.
2. Integridad de contenedor (si aplica).
3. Presencia de metadatos de Powersim.
4. Tamaño máximo: 100 KB.
""")