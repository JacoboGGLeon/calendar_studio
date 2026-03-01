import streamlit as st

def load_css():
    """
    Injects custom CSS for the Studio theme.
    """
    st.markdown("""
<style>
:root{
  --bg: #0b1020;
  --panel: rgba(255,255,255,.06);
  --border: rgba(255,255,255,.10);
  --text: rgba(255,255,255,.92);
  --accent: #7c5cff;
}

.stApp{
  background:
    radial-gradient(1200px 500px at 10% -10%, rgba(124,92,255,.15), transparent 60%),
    linear-gradient(180deg, var(--bg), #070a14 60%, #050712);
  color: var(--text);
}

.block-container { 
    padding-top: 5rem !important; 
    padding-bottom: 5rem !important;
}

/* Cards */
div.css-card {
  border-radius: 14px;
  border: 1px solid var(--border);
  background: rgba(255,255,255,.05);
  padding: 16px;
  margin-bottom: 10px;
}

/* User Requested Colors for Calendar Grid (Only inside columns) */
div[data-testid="stColumn"] button[kind="primary"], div[data-testid="stColumn"] [data-testid="stBaseButton-primary"] {
    background-color: rgba(100, 120, 145, 0.5) !important;
    border-color: rgba(100, 120, 145, 0.5) !important;
    color: white !important;
}
div[data-testid="stColumn"] button[kind="primary"]:hover, div[data-testid="stColumn"] [data-testid="stBaseButton-primary"]:hover {
    background-color: rgba(100, 120, 145, 0.8) !important;
    border-color: rgba(100, 120, 145, 0.8) !important;
}

div[data-testid="stColumn"] button[kind="secondary"], div[data-testid="stColumn"] [data-testid="stBaseButton-secondary"] {
    background-color: rgba(150, 110, 120, 0.5) !important;
    border-color: rgba(150, 110, 120, 0.5) !important;
    color: white !important;
}
div[data-testid="stColumn"] button[kind="secondary"]:hover, div[data-testid="stColumn"] [data-testid="stBaseButton-secondary"]:hover {
    background-color: rgba(150, 110, 120, 0.8) !important;
    border-color: rgba(150, 110, 120, 0.8) !important;
}

/* User Requested: Orange Outline for Selected Day in Paint Mode */
/* User Requested: White Outline for Selected Day in Paint Mode */
div[data-testid="stElementContainer"]:has(.selected-marker),
div.element-container:has(.selected-marker) {
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

div[data-testid="stElementContainer"]:has(.selected-marker) + div[data-testid="stElementContainer"] button,
div.element-container:has(.selected-marker) + div.element-container button {
    border: 3px solid rgba(255, 255, 255, 0.95) !important;
    box-shadow: 0 0 10px rgba(255, 255, 255, 0.7) !important;
}

/* User Requested: Blue Outline for Actual Today */
div[data-testid="stElementContainer"]:has(.today-marker),
div.element-container:has(.today-marker) {
    display: none !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}

div[data-testid="stElementContainer"]:has(.today-marker) + div[data-testid="stElementContainer"] button,
div.element-container:has(.today-marker) + div.element-container button {
    border: 3px solid #1c83e1 !important;
    box-shadow: 0 0 10px rgba(28, 131, 225, 1) !important;
}
</style>
""", unsafe_allow_html=True)
