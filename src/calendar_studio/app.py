"""Optional interface: the same public API used by notebooks and services."""

from io import BytesIO
import pandas as pd
import streamlit as st
from calendar_studio import CalendarStudio
from calendar_studio.core import holiday_dates

st.set_page_config(page_title="Calendar Studio", layout="wide")
st.title("Calendar Studio")
st.caption(
    "Generación de calendarios con festivos explícitos. Las reglas son configuraciones de proyecto, no asesoría fiscal."
)
profile = st.selectbox("Perfil", ["generic", "mac_legacy_v1"])
a, b = st.columns(2)
start = a.date_input("Desde", value=pd.Timestamp("2026-01-01").date())
end = b.date_input("Hasta", value=pd.Timestamp("2026-12-31").date())
file = st.file_uploader("Festivos · CSV o Parquet con columna fecha", type=["csv", "parquet"])
empty = st.checkbox("Usar deliberadamente un calendario sin festivos")
if st.button("Generar calendario"):
    try:
        if file is None and not empty:
            raise ValueError("Carga los festivos o indica explícitamente que no hay")
        if file is not None and empty:
            raise ValueError("Elige archivo o calendario sin festivos")
        holidays = (
            []
            if empty
            else holiday_dates(
                pd.read_parquet(file) if file.name.endswith(".parquet") else pd.read_csv(file), "fecha"
            )
        )
        studio = CalendarStudio.from_profile(profile) if profile != "generic" else CalendarStudio()
        artifact = studio.generate(start=start, end=end, holidays=holidays)
        st.session_state["calendar"] = artifact
    except (ValueError, TypeError) as exc:
        st.error(str(exc))
if "calendar" in st.session_state:
    artifact = st.session_state["calendar"]
    frame = artifact.to_pandas()
    st.success(
        f"{len(frame)} fechas · {len(frame.columns) - 1} variables · validación {artifact.validate().ok}"
    )
    st.dataframe(frame, use_container_width=True, hide_index=True)
    output = BytesIO()
    frame.to_parquet(output, index=False, compression="zstd")
    st.download_button("Descargar Parquet", data=output.getvalue(), file_name="calendar.parquet")
    st.download_button("Descargar CSV", data=frame.to_csv(index=False).encode(), file_name="calendar.csv")
