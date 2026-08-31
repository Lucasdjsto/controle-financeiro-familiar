import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Sistema Integrado de Gestão Financeira", layout="wide")

# --- CONTROLE DE ACESSO / AUTENTICAÇÃO ---
def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if st.session_state["autenticado"]:
        return True

    st.title("🔒 Acesso Restrito - Gestão Financeira")
    senha_correta = os.getenv("APP_PASSWORD", "123456")  # Valor padrão de segurança
    
    with st.form("form_login"):
        senha_digitada = st.text_input("Digite a senha de acesso:", type="password")
        botao_entrar = st.form_submit_button("Entrar")
        
        if botao_entrar:
            if senha_digitada == senha_correta:
                st.session_state["autenticado"] = True
                st.success("Acesso liberado!")
                st.rerun()
            else:
                st.error("Senha incorreta! Tente novamente.")
    return False

if not verificar_senha():
    st.stop()

# --- CONEXÃO COM BANCO DE DADOS SUPABASE ---
@st.cache_resource
def get_db_engine():
    db_url = os.getenv("POSTGRES_URL")
    if not db_url:
        st.error("❌ Variável POSTGRES_URL não configurada no Render.")
        st.stop()
    if "sslmode" not in db_url:
        db_url += "?sslmode=require" if "?" not in db_url else "&sslmode=require"
    return create_engine(db_url, connect_args={"connect_timeout": 10}, pool_pre_ping=True)

engine = get_db_engine()

# Inicialização das Tabelas no Supabase
def init_db():
    with engine.begin() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS projecao (
                pessoa TEXT,
                tipo TEXT,
                item TEXT,
                mes_ano TEXT,
                valor DOUBLE PRECISION DEFAULT 0,
                PRIMARY KEY (pessoa, tipo, item, mes_ano)
            );
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS gastos_fixos (
                id SERIAL PRIMARY KEY,
                pessoa TEXT,
                item TEXT,
                valor DOUBLE PRECISION DEFAULT 0
            );
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS pontuais_dinheiro (
                id SERIAL PRIMARY KEY,
                mes_ano TEXT,
                pessoa TEXT,
                descricao TEXT,
                categoria TEXT,
                valor DOUBLE PRECISION DEFAULT 0
            );
        '''))

init_db()

MESES_PROJECAO = [
    "08.2026", "09.2026", "10.2026", "11.2026", "12.2026",
    "01.2027", "02.2027", "03.2027", "04.2027", "05.2027"
]

ESTRUTURA_CARTÕES = {
    "Pessoa 1": ["C6 Carbon", "Nubank", "Santander"],
    "Pessoa 2": ["Banco do Brasil", "Rico / C6", "Amazon"]
}

ESTRUTURA_RECEITAS = {
    "Pessoa 1": ["Salário Base", "Receita Extra"],
    "Pessoa 2": ["Salário Base", "Receita Extra"]
}

def carregar_projecao(pessoa, tipo):
    query = "SELECT * FROM projecao WHERE pessoa = :pessoa AND tipo = :tipo"
    return pd.read_sql(text(query), engine, params={"pessoa": pessoa, "tipo": tipo})

def salvar_projecao(pessoa, tipo, df_editado):
    with engine.begin() as conn:
        for _, row in df_editado.iterrows():
            item = row['Item']
            for mes in MESES_PROJECAO:
                val = float(row[mes]) if pd.notnull(row[mes]) else 0.0
                query = '''
                    INSERT INTO projecao (pessoa, tipo, item, mes_ano, valor)
                    VALUES (:pessoa, :tipo, :item, :mes, :val)
                    ON CONFLICT (pessoa, tipo, item, mes_ano) 
                    DO UPDATE SET valor = EXCLUDED.valor;
                '''
                conn.execute(text(query), {"pessoa": pessoa, "tipo": tipo, "item": item, "mes": mes, "val": val})

def carregar_fixos(pessoa):
    query = "SELECT id, item, valor FROM gastos_fixos WHERE pessoa = :pessoa"
    return pd.read_sql(text(query), engine, params={"pessoa": pessoa})

def salvar_fixos(pessoa, df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gastos_fixos WHERE pessoa = :pessoa"), {"pessoa": pessoa})
        for _, row in df_editado.iterrows():
            if str(row['item']).strip():
                query = "INSERT INTO gastos_fixos (pessoa, item, valor) VALUES (:pessoa, :item, :val)"
                conn.execute(text(query), {"pessoa": pessoa, "item": str(row['item']), "val": float(row['valor'])})

def carregar_pontuais(mes_ano):
    query = "SELECT id, pessoa, descricao, categoria, valor FROM pontuais_dinheiro WHERE mes_ano = :mes_ano"
    return pd.read_sql(text(query), engine, params={"mes_ano": mes_ano})

def salvar_pontuais(mes_ano, df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM pontuais_dinheiro WHERE mes_ano = :mes_ano"), {"mes_ano": mes_ano})
        for _, row in df_editado.iterrows():
            if str(row['descricao']).strip():
                query = "INSERT INTO pontuais_dinheiro (mes_ano, pessoa, descricao, categoria, valor) VALUES (:mes_ano, :pessoa, :desc, :cat, :val)"
                conn.execute(text(query), {
                    "mes_ano": mes_ano, 
                    "pessoa": str(row['pessoa']), 
                    "desc": str(row['descricao']), 
                    "cat": str(row['categoria']), 
                    "val": float(row['valor'])
                })

# --- INTERFACE PRINCIPAL ---
col_head, col_logout = st.columns([8, 2])
with col_head:
    st.title("📊 Painel Financeiro Integrado & Projeção")
with col_logout:
    if st.button("🚪 Sair"):
        st.session_state["autenticado"] = False
        st.rerun()

tab_p1, tab_p2, tab_pontuais, tab_consolidado = st.tabs([
    "👤 Pessoa 1 (Lucas)", 
    "👤 Pessoa 2 (Marcella)", 
    "💸 Gastos Pontuais (Dinheiro/PIX)",
    "🏠 Visão Consolidada & Totais"
])

def renderizar_pessoa(pessoa):
    st.subheader("💵 1. Receitas (Salário e Rendimentos)")
    df_rec_db = carregar_projecao(pessoa, "RECEITA")
    rows_rec = []
    for item in ESTRUTURA_RECEITAS[pessoa]:
        row_dict = {"Item": item}
        for mes in MESES_PROJECAO:
            val = df_rec_db[(df_rec_db['item'] == item) & (df_rec_db['mes_ano'] == mes)]['valor']
            row_dict[mes] = float(val.iloc[0]) if not val.empty else 0.0
        rows_rec.append(row_dict)
    
    df_rec_grid = pd.DataFrame(rows_rec)
    df_rec_edit = st.data_editor(
        df_rec_grid, num_rows="fixed", use_container_width=True, key=f"rec_{pessoa}",
        column_config={mes: st.column_config.NumberColumn(f"{mes}", format="R$ %.2f", min_value=0.0) for mes in MESES_PROJECAO}
    )
    if st.button(f"💾 Salvar Receitas - {pessoa}"):
        salvar_projecao(pessoa, "RECEITA", df_rec_edit)
        st.success("Receitas salvas no banco de dados definitivo!")
        st.rerun()

    st.divider()

    st.subheader("💳 2. Evolução das Faturas de Cartão de Crédito")
    df_cart_db = carregar_projecao(pessoa, "CARTAO")
    rows_cart = []
    for item in ESTRUTURA_CARTÕES[pessoa]:
        row_dict = {"Item": item}
        for mes in MESES_PROJECAO:
            val = df_cart_db[(df_cart_db['item'] == item) & (df_cart_db['mes_ano'] == mes)]['valor']
            row_dict[mes] = float(val.iloc[0]) if not val.empty else 0.0
        rows_cart.append(row_dict)
        
    df_cart_grid = pd.DataFrame(rows_cart)
    df_cart_edit = st.data_editor(
        df_cart_grid, num_rows="fixed", use_container_width=True, key=f"cart_{pessoa}",
        column_config={mes: st.column_config.NumberColumn(f"{mes}", format="R$ %.2f", min_value=0.0) for mes in MESES_PROJECAO}
    )
    if st.button(f"💾 Salvar Cartões - {pessoa}"):
        salvar_projecao(pessoa, "CARTAO", df_cart_edit)
        st.success("Cartões salvos no banco de dados definitivo!")
        st.rerun()

    st.divider()

    st.subheader("📌 3. Gastos Fixos Recorrentes (Previsão Mensal Automática)")
    df_fixos_db = carregar_fixos(pessoa)
    df_fixos_edit = st.data_editor(
        df_fixos_db, num_rows="dynamic", use_container_width=True, key=f"fixos_{pessoa}",
        column_config={
            "item": st.column_config.TextColumn("Descrição do Gasto Fixo"),
            "valor": st.column_config.NumberColumn("Valor Mensal (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    if st.button(f"💾 Salvar Gastos Fixos - {pessoa}"):
        salvar_fixos(pessoa, df_fixos_edit)
        st.success("Gastos fixos salvos no banco de dados definitivo!")
        st.rerun()

    return df_rec_edit, df_cart_edit, df_fixos_edit

with tab_p1:
    rec_p1, cart_p1, fixos_p1 = renderizar_pessoa("Pessoa 1")

with tab_p2:
    rec_p2, cart_p2, fixos_p2 = renderizar_pessoa("Pessoa 2")

with tab_pontuais:
    st.header("💸 Gastos Pontuais em Dinheiro e PIX (Mês Corrente)")
    col_sel_p, _ = st.columns([2, 3])
    with col_sel_p:
        mes_pontual = st.selectbox("Selecione o Mês de Trabalho:", MESES_PROJECAO, index=0)
        
    df_pontuais_db = carregar_pontuais(mes_pontual)
    
    df_pontuais_edit = st.data_editor(
        df_pontuais_db, num_rows="dynamic", use_container_width=True, key="pontuais_editor",
        column_config={
            "pessoa": st.column_config.SelectboxColumn("Pessoa", options=["Pessoa 1", "Pessoa 2"]),
            "descricao": st.column_config.TextColumn("Descrição do Gasto"),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=["Mercado", "Padaria", "Transporte", "Lazer", "Farmácia", "Outros"]),
            "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    if st.button("💾 Salvar Gastos Pontuais"):
        salvar_pontuais(mes_pontual, df_pontuais_edit)
        st.success(f"Gastos pontuais de {mes_pontual} salvos no banco de dados definitivo!")
        st.rerun()

with tab_consolidado:
    st.header("🏠 Visão Consolidada da Família")
    
    def extrair_totais_completos():
        totais = {mes: {"rec_p1": 0, "cart_p1": 0, "fixos_p1": fixos_p1['valor'].sum(),
                        "rec_p2": 0, "cart_p2": 0, "fixos_p2": fixos_p2['valor'].sum(),
                        "pont_p1": 0, "pont_p2": 0} for mes in MESES_PROJECAO}
        
        for mes in MESES_PROJECAO:
            totais[mes]["rec_p1"] = rec_p1[mes].sum()
            totais[mes]["cart_p1"] = cart_p1[mes].sum()
            totais[mes]["rec_p2"] = rec_p2[mes].sum()
            totais[mes]["cart_p2"] = cart_p2[mes].sum()
            
            df_p = carregar_pontuais(mes)
            totais[mes]["pont_p1"] = df_p[df_p['pessoa'] == 'Pessoa 1']['valor'].sum() if not df_p.empty else 0
            totais[mes]["pont_p2"] = df_p[df_p['pessoa'] == 'Pessoa 2']['valor'].sum() if not df_p.empty else 0
            
        return totais

    totais_gerais = extrair_totais_completos()

    st.subheader("📌 Análise Detalhada do Mês Selecionado")
    mes_foco = st.selectbox("Selecione o mês para examinar em detalhe:", MESES_PROJECAO, index=0)
    
    t_foco = totais_gerais[mes_foco]
    
    r_p1 = t_foco["rec_p1"]
    d_p1 = t_foco["cart_p1"] + t_foco["fixos_p1"] + t_foco["pont_p1"]
    s_p1 = r_p1 - d_p1
    
    r_p2 = t_foco["rec_p2"]
    d_p2 = t_foco["cart_p2"] + t_foco["fixos_p2"] + t_foco["pont_p2"]
    s_p2 = r_p2 - d_p2
    
    r_fam = r_p1 + r_p2
    d_fam = d_p1 + d_p2
    s_fam = r_fam - d_fam
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(f"**Pessoa 1 ({mes_foco})**")
        st.metric("Receita Total", f"R$ {r_p1:,.2f}")
        st.metric("Despesas Totais", f"R$ {d_p1:,.2f}")
        st.metric("Sobra do Mês", f"R$ {s_p1:,.2f}")
        
    with c2:
        st.markdown(f"**Pessoa 2 ({mes_foco})**")
        st.metric("Receita Total", f"R$ {r_p2:,.2f}")
        st.metric("Despesas Totais", f"R$ {d_p2:,.2f}")
        st.metric("Sobra do Mês", f"R$ {s_p2:,.2f}")
        
    with c3:
        st.markdown(f"**TOTAL FAMÍLIA ({mes_foco})**")
        st.metric("Renda Familiar", f"R$ {r_fam:,.2f}")
        st.metric("Despesa Familiar", f"R$ {d_fam:,.2f}")
        st.metric("Sobra Família", f"R$ {s_fam:,.2f}")

    st.divider()

    st.subheader("📅 Projeção Evolutiva Mês a Mês & Total Geral Acumulado")
    
    row_rec = {"Métrica": "Renda Total Família"}
    row_cart = {"Métrica": "Despesas Cartões"}
    row_fixos = {"Métrica": "Gastos Fixos (Recorrentes)"}
    row_pontuais = {"Métrica": "Gastos Pontuais (Dinheiro/PIX)"}
    row_desp = {"Métrica": "Despesa Total Família"}
    row_sobra = {"Métrica": "Sobra do Mês"}
    
    tot_rec_g, tot_desp_g = 0, 0
    
    for mes in MESES_PROJECAO:
        tg = totais_gerais[mes]
        rf = tg["rec_p1"] + tg["rec_p2"]
        cf = tg["cart_p1"] + tg["cart_p2"]
        ff = tg["fixos_p1"] + tg["fixos_p2"]
        pf = tg["pont_p1"] + tg["pont_p2"]
        df = cf + ff + pf
        sf = rf - df
        
        row_rec[mes] = rf
        row_cart[mes] = cf
        row_fixos[mes] = ff
        row_pontuais[mes] = pf
        row_desp[mes] = df
        row_sobra[mes] = sf
        
        tot_rec_g += rf
        tot_desp_g += df
        
    row_rec["TOTAL GERAL"] = tot_rec_g
    row_cart["TOTAL GERAL"] = sum(totais_gerais[m]["cart_p1"] + totais_gerais[m]["cart_p2"] for m in MESES_PROJECAO)
    row_fixos["TOTAL GERAL"] = sum(totais_gerais[m]["fixos_p1"] + totais_gerais[m]["fixos_p2"] for m in MESES_PROJECAO)
    row_pontuais["TOTAL GERAL"] = sum(totais_gerais[m]["pont_p1"] + totais_gerais[m]["pont_p2"] for m in MESES_PROJECAO)
    row_desp["TOTAL GERAL"] = tot_desp_g
    row_sobra["TOTAL GERAL"] = tot_rec_g - tot_desp_g

    df_resumo = pd.DataFrame([row_rec, row_cart, row_fixos, row_pontuais, row_desp, row_sobra])
    
    cols_conf = {mes: st.column_config.NumberColumn(format="R$ %.2f") for mes in MESES_PROJECAO}
    cols_conf["TOTAL GERAL"] = st.column_config.NumberColumn("TOTAL GERAL PERÍODO", format="R$ %.2f")

    st.dataframe(df_resumo, use_container_width=True, column_config=cols_conf)
