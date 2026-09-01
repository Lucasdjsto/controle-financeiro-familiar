import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# 1. Configuração da Página
st.set_page_config(page_title="Sistema Integrado de Gestão Financeira", layout="wide")

# 2. Injeção de CSS Otimizado para Mobile e Destaques Visuais
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 1.5rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        .stMetric {
            background-color: #1e293b;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #334155;
        }
        @media (max-width: 640px) {
            h1 { font-size: 1.5rem !important; }
            h2 { font-size: 1.2rem !important; }
            h3 { font-size: 1.0rem !important; }
            [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
            .stDataFrame { font-size: 0.85rem; }
        }
    </style>
""", unsafe_allow_html=True)

# 3. Autenticação por Senha
def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if st.session_state["autenticado"]:
        return True

    st.title("🔒 Acesso Restrito - Gestão Financeira")
    senha_correta = os.getenv("APP_PASSWORD") or st.secrets.get("APP_PASSWORD", "123456")
    
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

# 4. Conexão Otimizada com o Banco de Dados (Engine Pool)
@st.cache_resource
def get_db_engine():
    db_url = os.getenv("POSTGRES_URL") or st.secrets.get("postgres", {}).get("url")
    if not db_url:
        st.error("❌ Variável de conexão com o banco não configurada.")
        st.stop()
    if "sslmode" not in db_url:
        db_url += "?sslmode=require" if "?" not in db_url else "&sslmode=require"
    
    return create_engine(
        db_url,
        pool_size=5,
        max_overflow=10,
        pool_recycle=300,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10}
    )

engine = get_db_engine()

# 5. Inicialização das Tabelas no Banco
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
            CREATE TABLE IF NOT EXISTS gastos_comuns (
                id SERIAL PRIMARY KEY,
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
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS caixinha (
                mes_ano TEXT PRIMARY KEY,
                valor DOUBLE PRECISION DEFAULT 0
            );
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS programado_cartao (
                id SERIAL PRIMARY KEY,
                pessoa TEXT,
                cartao TEXT,
                descricao TEXT,
                valor DOUBLE PRECISION DEFAULT 0
            );
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS dinheiro_provisionado (
                id SERIAL PRIMARY KEY,
                pessoa TEXT,
                descricao TEXT,
                valor DOUBLE PRECISION DEFAULT 0
            );
        '''))

init_db()

# 6. Constantes e Estruturas
MESES_PROJECAO = [
    "08.2026", "09.2026", "10.2026", "11.2026", "12.2026",
    "01.2027", "02.2027", "03.2027", "04.2027", "05.2027", "06.2027", "07.2027",
    "08.2027", "09.2027", "10.2027", "11.2027", "12.2027",
    "01.2028", "02.2028", "03.2028", "04.2028", "05.2028", "06.2028", "07.2028"
]

ESTRUTURA_CARTÕES = {
    "Pessoa 1": ["C6 Carbon", "Nubank", "Santander"],
    "Pessoa 2": ["Banco do Brasil", "Rico / C6", "Amazon"]
}

ESTRUTURA_RECEITAS = {
    "Pessoa 1": ["Salário Base", "Receita Extra"],
    "Pessoa 2": ["Salário Base", "Receita Extra"]
}

# 7. Funções de Leitura com Cache Inteligente (@st.cache_data)
@st.cache_data(ttl=600)
def carregar_projecao(pessoa, tipo):
    query = "SELECT * FROM projecao WHERE pessoa = :pessoa AND tipo = :tipo"
    return pd.read_sql(text(query), engine, params={"pessoa": pessoa, "tipo": tipo})

@st.cache_data(ttl=600)
def carregar_todas_projecoes(tipo):
    query = "SELECT * FROM projecao WHERE tipo = :tipo"
    return pd.read_sql(text(query), engine, params={"tipo": tipo})

@st.cache_data(ttl=600)
def carregar_fixos(pessoa):
    query = "SELECT id, item, valor FROM gastos_fixos WHERE pessoa = :pessoa"
    return pd.read_sql(text(query), engine, params={"pessoa": pessoa})

@st.cache_data(ttl=600)
def carregar_comuns():
    query = "SELECT id, item, valor FROM gastos_comuns"
    return pd.read_sql(text(query), engine)

@st.cache_data(ttl=600)
def carregar_pontuais(mes_ano):
    query = "SELECT id, pessoa, descricao, categoria, valor FROM pontuais_dinheiro WHERE mes_ano = :mes_ano"
    return pd.read_sql(text(query), engine, params={"mes_ano": mes_ano})

@st.cache_data(ttl=600)
def carregar_todos_pontuais():
    query = "SELECT mes_ano, pessoa, valor FROM pontuais_dinheiro"
    return pd.read_sql(text(query), engine)

@st.cache_data(ttl=600)
def carregar_caixinha():
    query = "SELECT mes_ano, valor FROM caixinha"
    return pd.read_sql(text(query), engine)

@st.cache_data(ttl=600)
def carregar_programado_cartao(pessoa):
    query = "SELECT id, cartao, descricao, valor FROM programado_cartao WHERE pessoa = :pessoa"
    return pd.read_sql(text(query), engine, params={"pessoa": pessoa})

@st.cache_data(ttl=600)
def carregar_dinheiro_provisionado(pessoa):
    query = "SELECT id, descricao, valor FROM dinheiro_provisionado WHERE pessoa = :pessoa"
    return pd.read_sql(text(query), engine, params={"pessoa": pessoa})

# 8. Funções de Escrita
def salvar_projecao(pessoa, tipo, df_editado, meses_visiveis):
    with engine.begin() as conn:
        for _, row in df_editado.iterrows():
            item = row['Item']
            for mes in meses_visiveis:
                val = float(row[mes]) if pd.notnull(row[mes]) else 0.0
                query = '''
                    INSERT INTO projecao (pessoa, tipo, item, mes_ano, valor)
                    VALUES (:pessoa, :tipo, :item, :mes, :val)
                    ON CONFLICT (pessoa, tipo, item, mes_ano) 
                    DO UPDATE SET valor = EXCLUDED.valor;
                '''
                conn.execute(text(query), {"pessoa": pessoa, "tipo": tipo, "item": item, "mes": mes, "val": val})

def salvar_fixos(pessoa, df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gastos_fixos WHERE pessoa = :pessoa"), {"pessoa": pessoa})
        for _, row in df_editado.iterrows():
            if str(row['item']).strip():
                query = "INSERT INTO gastos_fixos (pessoa, item, valor) VALUES (:pessoa, :item, :val)"
                conn.execute(text(query), {"pessoa": pessoa, "item": str(row['item']), "val": float(row['valor'])})

def salvar_comuns(df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gastos_comuns"))
        for _, row in df_editado.iterrows():
            if str(row['item']).strip():
                query = "INSERT INTO gastos_comuns (item, valor) VALUES (:item, :val)"
                conn.execute(text(query), {"item": str(row['item']), "val": float(row['valor'])})

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

def salvar_caixinha(df_editado):
    with engine.begin() as conn:
        for _, row in df_editado.iterrows():
            mes = row['Mês']
            val = float(row['Aporte do Mês (R$)']) if pd.notnull(row['Aporte do Mês (R$)']) else 0.0
            query = '''
                INSERT INTO caixinha (mes_ano, valor)
                VALUES (:mes, :val)
                ON CONFLICT (mes_ano)
                DO UPDATE SET valor = EXCLUDED.valor;
            '''
            conn.execute(text(query), {"mes": mes, "val": val})

def salvar_programado_cartao(pessoa, df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM programado_cartao WHERE pessoa = :pessoa"), {"pessoa": pessoa})
        for _, row in df_editado.iterrows():
            if str(row['descricao']).strip():
                query = "INSERT INTO programado_cartao (pessoa, cartao, descricao, valor) VALUES (:pessoa, :cartao, :desc, :val)"
                conn.execute(text(query), {"pessoa": pessoa, "cartao": str(row['cartao']), "desc": str(row['descricao']), "val": float(row['valor'])})

def salvar_dinheiro_provisionado(pessoa, df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dinheiro_provisionado WHERE pessoa = :pessoa"), {"pessoa": pessoa})
        for _, row in df_editado.iterrows():
            if str(row['descricao']).strip():
                query = "INSERT INTO dinheiro_provisionado (pessoa, descricao, valor) VALUES (:pessoa, :desc, :val)"
                conn.execute(text(query), {"pessoa": pessoa, "desc": str(row['descricao']), "val": float(row['valor'])})

# 9. Cabeçalho e Botão Unificado de Salvamento
col_head, col_save_all, col_logout = st.columns([6, 3, 1])
with col_head:
    st.title("📊 Painel Financeiro Integrado")

with col_save_all:
    if st.button("💾 SALVAR TODAS AS ALTERAÇÕES", type="primary", use_container_width=True):
        if "rec_p1_df" in st.session_state: salvar_projecao("Pessoa 1", "RECEITA", st.session_state["rec_p1_df"], st.session_state["meses_v"])
        if "cart_p1_df" in st.session_state: salvar_projecao("Pessoa 1", "CARTAO", st.session_state["cart_p1_df"], st.session_state["meses_v"])
        if "fix_p1_df" in st.session_state: salvar_fixos("Pessoa 1", st.session_state["fix_p1_df"])
        if "prog_p1_df" in st.session_state: salvar_programado_cartao("Pessoa 1", st.session_state["prog_p1_df"])
        if "prov_p1_df" in st.session_state: salvar_dinheiro_provisionado("Pessoa 1", st.session_state["prov_p1_df"])

        if "rec_p2_df" in st.session_state: salvar_projecao("Pessoa 2", "RECEITA", st.session_state["rec_p2_df"], st.session_state["meses_v"])
        if "cart_p2_df" in st.session_state: salvar_projecao("Pessoa 2", "CARTAO", st.session_state["cart_p2_df"], st.session_state["meses_v"])
        if "fix_p2_df" in st.session_state: salvar_fixos("Pessoa 2", st.session_state["fix_p2_df"])
        if "prog_p2_df" in st.session_state: salvar_programado_cartao("Pessoa 2", st.session_state["prog_p2_df"])
        if "prov_p2_df" in st.session_state: salvar_dinheiro_provisionado("Pessoa 2", st.session_state["prov_p2_df"])

        if "comuns_df" in st.session_state: salvar_comuns(st.session_state["comuns_df"])
        if "caixinha_df" in st.session_state: salvar_caixinha(st.session_state["caixinha_df"])
        
        st.cache_data.clear()
        st.success("Tudo foi salvo com sucesso!")
        st.rerun()

with col_logout:
    if st.button("🚪 Sair"):
        st.session_state["autenticado"] = False
        st.rerun()

# 10. LÓGICA DE CÁLCULO DE CAIXA E ACÚMULO SEQUENCIAL
def calcular_sequencia_financeira():
    rec_all_db = carregar_todas_projecoes("RECEITA")
    cart_all_db = carregar_todas_projecoes("CARTAO")
    
    prog_cart_p1 = carregar_programado_cartao("Pessoa 1")['valor'].sum()
    prog_cart_p2 = carregar_programado_cartao("Pessoa 2")['valor'].sum()
    
    tot_prov_din = carregar_dinheiro_provisionado("Pessoa 1")['valor'].sum() + carregar_dinheiro_provisionado("Pessoa 2")['valor'].sum()
    tot_fixos = carregar_fixos("Pessoa 1")['valor'].sum() + carregar_fixos("Pessoa 2")['valor'].sum() + carregar_comuns()['valor'].sum()
    
    caixinha_df = carregar_caixinha()
    todos_pontuais_df = carregar_todos_pontuais()

    dados_meses = {}
    saldo_acumulado_anterior = 0.0

    for m in MESES_PROJECAO:
        renda_mes = rec_all_db[rec_all_db['mes_ano'] == m]['valor'].sum() if not rec_all_db.empty else 0.0
        
        c_val = cart_all_db[cart_all_db['mes_ano'] == m]['valor'].sum() if not cart_all_db.empty else 0.0
        cartao_mes = c_val + prog_cart_p1 + prog_cart_p2
        
        p_df = todos_pontuais_df[todos_pontuais_df['mes_ano'] == m] if not todos_pontuais_df.empty else pd.DataFrame()
        pontual_mes = p_df['valor'].sum() if not p_df.empty else 0.0
        
        caixinha_mes = caixinha_df[caixinha_df['mes_ano'] == m]['valor'].sum() if not caixinha_df.empty else 0.0

        saidas_mes = cartao_mes + tot_fixos + pontual_mes + tot_prov_din + caixinha_mes
        sobra_do_mes_bruta = renda_mes - saidas_mes
        
        saldo_conta_final = saldo_acumulado_anterior + sobra_do_mes_bruta

        dados_meses[m] = {
            "saldo_anterior": saldo_acumulado_anterior,
            "renda_mes": renda_mes,
            "saidas_mes": saidas_mes,
            "caixinha_mes": caixinha_mes,
            "sobra_mes_isolada": sobra_do_mes_bruta,
            "saldo_acumulado_final": saldo_conta_final
        }

        saldo_acumulado_anterior = saldo_conta_final

    return dados_meses

dados_financeiros = calcular_sequencia_financeira()

# --- ARQUIVAMENTO E SELEÇÃO DO MÊS DE FOCO ---
col_tit, col_sel, col_visao = st.columns([5, 3, 2])
with col_tit:
    st.markdown("### ⚡ Situação Atual do Mês")
with col_sel:
    mes_atual = st.selectbox("Selecione o Mês em Destaque:", MESES_PROJECAO, index=0)
with col_visao:
    modo_exibicao = st.radio("Janela Temporal:", ["Próximos 12 meses", "Todos os 24 meses"], index=0)

idx_foco = MESES_PROJECAO.index(mes_atual)
meses_visiveis = MESES_PROJECAO[idx_foco:idx_foco+12] if modo_exibicao == "Próximos 12 meses" else MESES_PROJECAO[idx_foco:]
st.session_state["meses_v"] = meses_visiveis

d_foco = dados_financeiros[mes_atual]

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Saldo Inicial Em Conta", f"R$ {d_foco['saldo_anterior']:,.2f}")
k2.metric("Renda do Mês", f"R$ {d_foco['renda_mes']:,.2f}")
k3.metric("Saídas Totais", f"R$ {d_foco['saidas_mes']:,.2f}")
k4.metric("Aporte Caixinha", f"R$ {d_foco['caixinha_mes']:,.2f}")

s_final = d_foco['saldo_acumulado_final']
if s_final >= 0:
    k5.metric("Saldo Acumulado Final", f"R$ {s_final:,.2f}", delta="Positivo", delta_color="normal")
else:
    k5.metric("Saldo Acumulado Final", f"R$ {s_final:,.2f}", delta="Déficit", delta_color="inverse")

st.divider()

# 11. Interface Principal (Abas)
tab_p1, tab_p2, tab_comuns, tab_pontuais, tab_consolidado = st.tabs([
    "👤 Pessoa 1 (Lucas)", 
    "👤 Pessoa 2 (Marcella)", 
    "🏡 Despesas Comuns (Casa/Aluguel)",
    "💸 Gastos Pontuais (Dinheiro/PIX)",
    "🏠 Visão Consolidada & Caixinha"
])

def renderizar_pessoa(pessoa, p_code):
    st.subheader("💵 1. Receitas (Salário e Rendimentos)")
    df_rec_db = carregar_projecao(pessoa, "RECEITA")
    rows_rec = []
    for item in ESTRUTURA_RECEITAS[pessoa]:
        row_dict = {"Item": item}
        for mes in meses_visiveis:
            val = df_rec_db[(df_rec_db['item'] == item) & (df_rec_db['mes_ano'] == mes)]['valor']
            row_dict[mes] = float(val.iloc[0]) if not val.empty else 0.0
        rows_rec.append(row_dict)
    
    df_rec_grid = pd.DataFrame(rows_rec)
    df_rec_edit = st.data_editor(
        df_rec_grid, num_rows="fixed", use_container_width=True, key=f"rec_{p_code}",
        column_config={mes: st.column_config.NumberColumn(f"{mes}", format="R$ %.2f", min_value=0.0) for mes in meses_visiveis}
    )
    st.session_state[f"rec_{p_code}_df"] = df_rec_edit

    st.divider()

    st.subheader("💳 2. Evolução das Faturas de Cartão de Crédito (Fechadas/Processadas)")
    df_cart_db = carregar_projecao(pessoa, "CARTAO")
    rows_cart = []
    for item in ESTRUTURA_CARTÕES[pessoa]:
        row_dict = {"Item": item}
        for mes in meses_visiveis:
            val = df_cart_db[(df_cart_db['item'] == item) & (df_cart_db['mes_ano'] == mes)]['valor']
            row_dict[mes] = float(val.iloc[0]) if not val.empty else 0.0
        rows_cart.append(row_dict)
        
    df_cart_grid = pd.DataFrame(rows_cart)
    df_cart_edit = st.data_editor(
        df_cart_grid, num_rows="fixed", use_container_width=True, key=f"cart_{p_code}",
        column_config={mes: st.column_config.NumberColumn(f"{mes}", format="R$ %.2f", min_value=0.0) for mes in meses_visiveis}
    )
    st.session_state[f"cart_{p_code}_df"] = df_cart_edit

    st.divider()

    st.subheader("🔮 3. Lançamentos Programados no Cartão (Seguros / Assinaturas Futuras)")
    df_prog_cart = carregar_programado_cartao(pessoa)
    df_prog_edit = st.data_editor(
        df_prog_cart, num_rows="dynamic", use_container_width=True, key=f"prog_{p_code}",
        column_config={
            "cartao": st.column_config.SelectboxColumn("Cartão", options=ESTRUTURA_CARTÕES[pessoa]),
            "descricao": st.column_config.TextColumn("Descrição (ex: Seguro, Netflix)"),
            "valor": st.column_config.NumberColumn("Valor Previsto (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    st.session_state[f"prog_{p_code}_df"] = df_prog_edit

    st.divider()

    st.subheader("📌 4. Gastos Fixos Individuais Recorrentes")
    df_fixos_db = carregar_fixos(pessoa)
    df_fixos_edit = st.data_editor(
        df_fixos_db, num_rows="dynamic", use_container_width=True, key=f"fix_{p_code}",
        column_config={
            "item": st.column_config.TextColumn("Descrição do Gasto Fixo Individual"),
            "valor": st.column_config.NumberColumn("Valor Mensal (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    st.session_state[f"fix_{p_code}_df"] = df_fixos_edit

    st.divider()

    st.subheader("💵 5. PIX / Dinheiro Certo (Desconto Automático da Renda)")
    df_prov_din = carregar_dinheiro_provisionado(pessoa)
    df_prov_edit = st.data_editor(
        df_prov_din, num_rows="dynamic", use_container_width=True, key=f"prov_{p_code}",
        column_config={
            "descricao": st.column_config.TextColumn("Descrição (ex: Barbeiro, Feira)"),
            "valor": st.column_config.NumberColumn("Valor Previsto (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    st.session_state[f"prov_{p_code}_df"] = df_prov_edit

with tab_p1:
    renderizar_pessoa("Pessoa 1", "p1")

with tab_p2:
    renderizar_pessoa("Pessoa 2", "p2")

with tab_comuns:
    st.header("🏡 Despesas Comuns do Casal / Casa")
    df_comuns_db = carregar_comuns()
    df_comuns_edit = st.data_editor(
        df_comuns_db, num_rows="dynamic", use_container_width=True, key="comuns_editor",
        column_config={
            "item": st.column_config.TextColumn("Descrição da Despesa Comum"),
            "valor": st.column_config.NumberColumn("Valor Mensal (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    st.session_state["comuns_df"] = df_comuns_edit

with tab_pontuais:
    st.header("💸 Gastos Pontuais em Dinheiro/PIX (Imprevistos do Mês)")
    col_sel_p, _ = st.columns([2, 3])
    with col_sel_p:
        mes_pontual = st.selectbox("Selecione o Mês:", MESES_PROJECAO, index=idx_foco)
        
    df_pontuais_db = carregar_pontuais(mes_pontual)
    
    df_pontuais_edit = st.data_editor(
        df_pontuais_db, num_rows="dynamic", use_container_width=True, key="pontuais_editor",
        column_config={
            "pessoa": st.column_config.SelectboxColumn("Pessoa", options=["Pessoa 1", "Pessoa 2", "Comum / Casa"]),
            "descricao": st.column_config.TextColumn("Descrição do Gasto"),
            "categoria": st.column_config.SelectboxColumn("Categoria", options=["Mercado", "Padaria", "Transporte", "Lazer", "Farmácia", "Outros"]),
            "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    if st.button("💾 Salvar Gastos Pontuais do Mês"):
        salvar_pontuais(mes_pontual, df_pontuais_edit)
        st.cache_data.clear()
        st.success(f"Gastos pontuais de {mes_pontual} salvos!")
        st.rerun()

with tab_consolidado:
    st.header("🏠 Visão Consolidada, Caixinha & Totais")
    
    st.subheader("📦 Caixinha de Reserva da Família (Acumulativa)")
    df_caixinha_db = carregar_caixinha()
    rows_caixinha = []
    
    for mes in meses_visiveis:
        val = df_caixinha_db[df_caixinha_db['mes_ano'] == mes]['valor']
        val_aporte = float(val.iloc[0]) if not val.empty else 0.0
        rows_caixinha.append({"Mês": mes, "Aporte do Mês (R$)": val_aporte})
        
    df_caixinha_grid = pd.DataFrame(rows_caixinha)
    df_caixinha_edit = st.data_editor(
        df_caixinha_grid, num_rows="fixed", use_container_width=True, key="caixinha_editor",
        column_config={
            "Mês": st.column_config.TextColumn("Mês", disabled=True),
            "Aporte do Mês (R$)": st.column_config.NumberColumn("Aporte do Mês (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    st.session_state["caixinha_df"] = df_caixinha_edit

    st.divider()

    st.subheader("📅 Projeção Evolutiva Mês a Mês & Saldo de Caixa Acumulado")
    
    row_sal_ini = {"Métrica": "1. Saldo Inicial em Conta"}
    row_rec = {"Métrica": "2. Renda Total Família"}
    row_desp = {"Métrica": "3. Saídas Totais (Cartão + Fixos + PIX)"}
    row_caixinha = {"Métrica": "4. Aporte Caixinha (Mês)"}
    row_sobra_mes = {"Métrica": "5. Sobra Líquida Isolada do Mês"}
    row_sal_fim = {"Métrica": "6. Saldo Final Acumulado em Conta"}

    for m in meses_visiveis:
        d = dados_financeiros[m]
        row_sal_ini[m] = d["saldo_anterior"]
        row_rec[m] = d["renda_mes"]
        row_desp[m] = d["saidas_mes"] - d["caixinha_mes"]
        row_caixinha[m] = d["caixinha_mes"]
        row_sobra_mes[m] = d["sobra_mes_isolada"]
        row_sal_fim[m] = d["saldo_acumulado_final"]

    df_resumo = pd.DataFrame([
        row_sal_ini, row_rec, row_desp, row_caixinha, row_sobra_mes, row_sal_fim
    ])
    
    cols_conf = {mes: st.column_config.NumberColumn(format="R$ %.2f") for mes in meses_visiveis}
    st.dataframe(df_resumo, use_container_width=True, column_config=cols_conf)
