import streamlit as st 
import pandas as pd
import io
import gdown

# ID del archivo
file_id = "1YafhQs3SZwKJqoOLoOg_Y9Q7DR0nibEo"

# URL directa de descarga
url = f"https://drive.google.com/uc?id={file_id}"

# Descargar la última versión del Excel en cada ejecución
gdown.download(url, "Prueba Correos Extraer.xlsx", quiet=False, fuzzy=True)

# Lista de hojas que queremos combinar
hojas = [
    'BOE Alertas de Anuncios',
    'BOE Alertas de Personal',
    'BOE Alertas legislativas',
    'BOE Alertas temáticas',
    'DOUE Alertas legislativas'
]

# Cargar y combinar las hojas
@st.cache_data
def cargar_datos():
    combined_df = pd.DataFrame()
    for hoja in hojas:
        df = pd.read_excel("Prueba Correos Extraer.xlsx", sheet_name=hoja)
        df['Fuente'] = hoja  # Añadimos de qué hoja viene
        combined_df = pd.concat([combined_df, df], ignore_index=True)
    # Aseguramos que 'Fecha correo' solo tenga la fecha (sin hora)
    combined_df['Fecha correo'] = pd.to_datetime(combined_df['Fecha correo']).dt.date
    return combined_df[['Fecha correo', 'Título', 'URL', 'Ver documento', 'Fuente', 'CPVs']]

# Cargar listado de CPVs desde la hoja "Listado CPV"
@st.cache_data
def cargar_cpvs():
    cpv_df = pd.read_excel("Prueba Correos Extraer.xlsx", sheet_name='Listado CPV')
    cpv_df = cpv_df.dropna(subset=['Código CPV', 'Descripción'])
    cpv_df['CPV_Completo'] = cpv_df['Código CPV'].astype(str) + " - " + cpv_df['Descripción']
    return sorted(cpv_df['CPV_Completo'].unique())

df = cargar_datos()
cpv_listado = cargar_cpvs()

st.title("Buscador - Alertas BOE y DOUE, se actualiza a las 16:00 todos los días (desde 08/05/2025)")
st.write(f"🔍 Total de registros disponibles: **{len(df)}**")
st.write("Usa los filtros para realizar una búsqueda. Si no aplicas ninguno, no se cargará nada para evitar demoras.")

# Función para crear hipervínculo solo si es válido
def linkify(value, text):
    if pd.notna(value) and str(value).startswith('http'):
        return f"[{text}]({value})"
    else:
        return "(sin enlace)"

# Mostrar todos los datos (opcional)
if st.checkbox("Mostrar todos los datos combinados (⚠️ puede tardar)"):
    df_display = df.copy()
    df_display['URL'] = df_display['URL'].apply(lambda x: linkify(x, 'Abrir enlace'))
    df_display['Ver documento'] = df_display['Ver documento'].apply(lambda x: linkify(x, 'Ver documento'))
    st.write(df_display.to_markdown(index=False), unsafe_allow_html=True)

# --- FILTROS UNIFICADOS ---

# Campo de búsqueda por título
busqueda = st.text_input("Búsqueda:")

# Multiselección de CPVs
opciones_cpv = cpv_listado
cpvs_seleccionados = st.multiselect("Selecciona uno o varios CPVs", opciones_cpv)

# Solo aplicamos filtros si hay algo
if busqueda or cpvs_seleccionados:
    filtros = df.copy()

    # Filtrar por búsqueda de texto (requiere todas las palabras)
    if busqueda:
        palabras = busqueda.split()
        # Generar una máscara que verifique si todas las palabras están en el título
        mask = df['Título'].apply(lambda x: all(palabra.lower() in str(x).lower() for palabra in palabras))
        resultados_texto = df[mask]
    else:
        resultados_texto = df  # Si no hay búsqueda, dejamos todo

    # Aplicar filtro por CPVs seleccionados
    if cpvs_seleccionados:
        resultados = resultados_texto[resultados_texto['CPVs'].apply(
            lambda cell: any(cpv in str(cell) for cpv in cpvs_seleccionados)
        )]
    else:
        resultados = resultados_texto

    # Mostrar resultados filtrados
    if not resultados.empty:
        st.write(f"✅ Resultados encontrados: **{len(resultados)}**")

        resultados_display = resultados.copy()
        resultados_display['URL'] = resultados_display['URL'].apply(lambda x: linkify(x, 'Abrir enlace'))
        resultados_display['Ver documento'] = resultados_display['Ver documento'].apply(lambda x: linkify(x, 'Ver documento'))
        st.write(resultados_display.to_markdown(index=False), unsafe_allow_html=True)

        # Preparar Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            resultados.to_excel(writer, index=False)
        excel_data = output.getvalue()

        # Botón para descargar
        st.download_button(
            label="📥 Descargar resultados filtrados (.xlsx)",
            data=excel_data,
            file_name="resultados_filtrados.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("No se encontraron resultados para los filtros aplicados.")
else:
    st.write("🔸 Esperando que apliques un filtro para mostrar resultados.")
