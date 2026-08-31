import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Sistema Integrado de Gestão Financeira", layout="wide")

st.title("📊 Painel Financeiro Integrado")

# Tentativa de Conexão com Log Explicito
try:
    if "postgres" not in st.secrets or "url" not in st.secrets["postgres"]:
        st.error("❌ A chave 'postgres.url' não foi encontrada na aba Secrets do Streamlit.")
        st.stop()

    db_url = st.secrets["postgres"]["url"]
    engine = create_engine(db_url, connect_args={"connect_timeout": 10})
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1;"))
        st.success("✅ Conexão com o banco de dados Supabase realizada com sucesso!")

except Exception as e:
    st.error("❌ Falha na conexão com o banco de dados PostgreSQL:")
    st.exception(e)
    st.stop()
