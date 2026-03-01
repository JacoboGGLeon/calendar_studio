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
div[data-testid="stColumn"] button[title="Selected Day"] {
    border: 2px solid rgba(255,153,0,0.4) !important;
}

/* User Requested: Bright Orange Outline for Actual Today */
div[data-testid="stColumn"] button[title="Today"] {
    border: 2px solid #ff9900 !important;
    box-shadow: 0 0 10px rgba(255,153,0,0.5) !important;
}
</style>
""", unsafe_allow_html=True)
