import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Sistema Integrado de Gestão Financeira", layout="wide")

@st.cache_resource
def get_db_engine():
    # Obtém a URL do ambiente do Render
    db_url = os.getenv("POSTGRES_URL")
    
    if not db_url:
        st.error("❌ A variável POSTGRES_URL não foi configurada nas Environment Variables do Render.")
        st.stop()
        
    # Garante suporte a SSL para conexões em nuvem
    if "sslmode" not in db_url:
        db_url += "?sslmode=require" if "?" not in db_url else "&sslmode=require"
        
    return create_engine(db_url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)

try:
    engine = get_db_engine()
except Exception as e:
    st.error(f"Erro ao inicializar o motor de banco de dados: {e}")
