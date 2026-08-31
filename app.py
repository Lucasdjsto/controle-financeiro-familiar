import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Sistema Integrado de Gestão Financeira", layout="wide")

@st.cache_resource
def get_db_engine():
    # Tenta ler do Render/Sistema e usa Secrets como alternativa
    db_url = os.getenv("POSTGRES_URL") or st.secrets.get("postgres", {}).get("url")
    return create_engine(db_url)

engine = get_db_engine()
