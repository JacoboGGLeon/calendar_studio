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

/* User Requested Colors for Calendar Grid */
button[kind="primary"], [data-testid="baseButton-primary"] {
    background-color: #555555 !important;
    border-color: #555555 !important;
    color: white !important;
}
button[kind="primary"]:hover, [data-testid="baseButton-primary"]:hover {
    background-color: #666666 !important;
    border-color: #666666 !important;
}

button[kind="secondary"], [data-testid="baseButton-secondary"] {
    background-color: #ffffff !important;
    border-color: #ffffff !important;
    color: #0b1020 !important;
}
button[kind="secondary"]:hover, [data-testid="baseButton-secondary"]:hover {
    background-color: #e6e6e6 !important;
    border-color: #e6e6e6 !important;
}
</style>
""", unsafe_allow_html=True)
