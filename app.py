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

# 7. Funções de Leitura com Cache Inteligente (@st.cache_data)
@st.cache_data(ttl=600)
def carregar_projecao(pessoa, tipo):
    query = "SELECT * FROM projecao WHERE pessoa = :pessoa AND tipo = :tipo"
    return pd.read_sql(text(query), engine, params={"pessoa": pessoa, "tipo": tipo})

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

# 8. Funções de Escrita com Invalidação de Cache
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
    st.cache_data.clear()

def salvar_fixos(pessoa, df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gastos_fixos WHERE pessoa = :pessoa"), {"pessoa": pessoa})
        for _, row in df_editado.iterrows():
            if str(row['item']).strip():
                query = "INSERT INTO gastos_fixos (pessoa, item, valor) VALUES (:pessoa, :item, :val)"
                conn.execute(text(query), {"pessoa": pessoa, "item": str(row['item']), "val": float(row['valor'])})
    st.cache_data.clear()

def salvar_comuns(df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gastos_comuns"))
        for _, row in df_editado.iterrows():
            if str(row['item']).strip():
                query = "INSERT INTO gastos_comuns (item, valor) VALUES (:item, :val)"
                conn.execute(text(query), {"item": str(row['item']), "val": float(row['valor'])})
    st.cache_data.clear()

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
    st.cache_data.clear()

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
    st.cache_data.clear()

def salvar_programado_cartao(pessoa, df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM programado_cartao WHERE pessoa = :pessoa"), {"pessoa": pessoa})
        for _, row in df_editado.iterrows():
            if str(row['descricao']).strip():
                query = "INSERT INTO programado_cartao (pessoa, cartao, descricao, valor) VALUES (:pessoa, :cartao, :desc, :val)"
                conn.execute(text(query), {"pessoa": pessoa, "cartao": str(row['cartao']), "desc": str(row['descricao']), "val": float(row['valor'])})
    st.cache_data.clear()

def salvar_dinheiro_provisionado(pessoa, df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM dinheiro_provisionado WHERE pessoa = :pessoa"), {"pessoa": pessoa})
        for _, row in df_editado.iterrows():
            if str(row['descricao']).strip():
                query = "INSERT INTO dinheiro_provisionado (pessoa, descricao, valor) VALUES (:pessoa, :desc, :val)"
                conn.execute(text(query), {"pessoa": pessoa, "desc": str(row['descricao']), "val": float(row['valor'])})
    st.cache_data.clear()

# 9. Cabeçalho e Logout
col_head, col_logout = st.columns([8, 2])
with col_head:
    st.title("📊 Painel Financeiro Integrado")
with col_logout:
    if st.button("🚪 Sair"):
        st.session_state["autenticado"] = False
        st.rerun()

# --- 10. CARD DE LIQUIDEZ INSTANTÂNEA (PRIMEIRA TELA - CORRIGIDO) ---
mes_atual = MESES_PROJECAO[0]  # "08.2026"

# 1. Carregamento e soma exata de Receitas do Mês Atual (Pessoa 1 + Pessoa 2)
rec_p1_db = carregar_projecao("Pessoa 1", "RECEITA")
rec_p2_db = carregar_projecao("Pessoa 2", "RECEITA")

tot_rec_p1 = rec_p1_db[rec_p1_db['mes_ano'] == mes_atual]['valor'].sum() if not rec_p1_db.empty else 0.0
tot_rec_p2 = rec_p2_db[rec_p2_db['mes_ano'] == mes_atual]['valor'].sum() if not rec_p2_db.empty else 0.0
tot_rec = tot_rec_p1 + tot_rec_p2

# 2. Carregamento e soma exata do Cartão de Crédito do Mês Atual
cart_p1_db = carregar_projecao("Pessoa 1", "CARTAO")
cart_p2_db = carregar_projecao("Pessoa 2", "CARTAO")

tot_cart_p1 = cart_p1_db[cart_p1_db['mes_ano'] == mes_atual]['valor'].sum() if not cart_p1_db.empty else 0.0
tot_cart_p2 = cart_p2_db[cart_p2_db['mes_ano'] == mes_atual]['valor'].sum() if not cart_p2_db.empty else 0.0

prog_cart_p1 = carregar_programado_cartao("Pessoa 1")['valor'].sum()
prog_cart_p2 = carregar_programado_cartao("Pessoa 2")['valor'].sum()

tot_cart = tot_cart_p1 + tot_cart_p2 + prog_cart_p1 + prog_cart_p2

# 3. Demais Despesas
tot_prov_din = carregar_dinheiro_provisionado("Pessoa 1")['valor'].sum() + carregar_dinheiro_provisionado("Pessoa 2")['valor'].sum()
tot_fixos = carregar_fixos("Pessoa 1")['valor'].sum() + carregar_fixos("Pessoa 2")['valor'].sum() + carregar_comuns()['valor'].sum()

pontuais_df = carregar_pontuais(mes_atual)
tot_pontuais = pontuais_df['valor'].sum() if not pontuais_df.empty else 0.0

caixinha_df = carregar_caixinha()
cax_val = caixinha_df[caixinha_df['mes_ano'] == mes_atual]['valor'].sum() if not caixinha_df.empty else 0.0

# 4. Cálculo da Liquidez Real
tot_despesas = tot_cart + tot_fixos + tot_pontuais + tot_prov_din + cax_val
sobra_liquida = tot_rec - tot_despesas

# Renderização do Card Superior
st.markdown(f"### ⚡ Situação Atual do Mês ({mes_atual})")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Renda Bruta", f"R$ {tot_rec:,.2f}")
k2.metric("Saídas Totais (Cartão/Fixos/PIX)", f"R$ {tot_despesas:,.2f}")
k3.metric("Aporte Caixinha", f"R$ {cax_val:,.2f}")

if sobra_liquida >= 0:
    k4.metric("Sobra do Mês", f"R$ {sobra_liquida:,.2f}", delta="Positivo", delta_color="normal")
else:
    k4.metric("Sombra/Déficit do Mês", f"R$ {sobra_liquida:,.2f}", delta="Negativo", delta_color="inverse")

st.divider()

# 11. Interface Principal (Abas)
tab_p1, tab_p2, tab_comuns, tab_pontuais, tab_consolidado = st.tabs([
    "👤 Pessoa 1 (Lucas)", 
    "👤 Pessoa 2 (Marcella)", 
    "🏡 Despesas Comuns (Casa/Aluguel)",
    "💸 Gastos Pontuais (Dinheiro/PIX)",
    "🏠 Visão Consolidada & Caixinha"
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
        st.success("Receitas salvas com sucesso!")
        st.rerun()

    st.divider()

    st.subheader("💳 2. Evolução das Faturas de Cartão de Crédito (Fechadas/Processadas)")
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
        st.success("Cartões salvos com sucesso!")
        st.rerun()

    st.divider()

    st.subheader("🔮 3. Lançamentos Programados no Cartão (Seguros / Assinaturas Futuras)")
    st.caption("Cadastre gastos certos que ainda não entraram na fatura para prever o valor real do cartão.")
    df_prog_cart = carregar_programado_cartao(pessoa)
    df_prog_edit = st.data_editor(
        df_prog_cart, num_rows="dynamic", use_container_width=True, key=f"prog_cart_{pessoa}",
        column_config={
            "cartao": st.column_config.SelectboxColumn("Cartão", options=ESTRUTURA_CARTÕES[pessoa]),
            "descricao": st.column_config.TextColumn("Descrição (ex: Seguro, Netflix)"),
            "valor": st.column_config.NumberColumn("Valor Previsto (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    if st.button(f"💾 Salvar Lançamentos Programados - {pessoa}"):
        salvar_programado_cartao(pessoa, df_prog_edit)
        st.success("Lançamentos programados salvos com sucesso!")
        st.rerun()

    st.divider()

    st.subheader("📌 4. Gastos Fixos Individuais Recorrentes")
    df_fixos_db = carregar_fixos(pessoa)
    df_fixos_edit = st.data_editor(
        df_fixos_db, num_rows="dynamic", use_container_width=True, key=f"fixos_{pessoa}",
        column_config={
            "item": st.column_config.TextColumn("Descrição do Gasto Fixo Individual"),
            "valor": st.column_config.NumberColumn("Valor Mensal (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    if st.button(f"💾 Salvar Gastos Fixos - {pessoa}"):
        salvar_fixos(pessoa, df_fixos_edit)
        st.success("Gastos fixos salvos com sucesso!")
        st.rerun()

    st.divider()

    st.subheader("💵 5. PIX / Dinheiro Certo (Desconto Automático da Renda)")
    st.caption("Gastos fixos em dinheiro que são liquidados logo no recebimento do salário.")
    df_prov_din = carregar_dinheiro_provisionado(pessoa)
    df_prov_edit = st.data_editor(
        df_prov_din, num_rows="dynamic", use_container_width=True, key=f"prov_din_{pessoa}",
        column_config={
            "descricao": st.column_config.TextColumn("Descrição (ex: Barbeiro, Feira)"),
            "valor": st.column_config.NumberColumn("Valor Previsto (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    if st.button(f"💾 Salvar PIX Certo - {pessoa}"):
        salvar_dinheiro_provisionado(pessoa, df_prov_edit)
        st.success("Gastos em dinheiro salvos com sucesso!")
        st.rerun()

    return df_rec_edit, df_cart_edit, df_fixos_edit

with tab_p1:
    rec_p1, cart_p1, fixos_p1 = renderizar_pessoa("Pessoa 1")

with tab_p2:
    rec_p2, cart_p2, fixos_p2 = renderizar_pessoa("Pessoa 2")

with tab_comuns:
    st.header("🏡 Despesas Comuns do Casal / Casa")
    st.info("Cadastre aqui as despesas que são compartilhadas (ex: Aluguel, Condomínio, Energia, Água, Internet, Mercado da Casa).")
    
    df_comuns_db = carregar_comuns()
    df_comuns_edit = st.data_editor(
        df_comuns_db, num_rows="dynamic", use_container_width=True, key="comuns_editor",
        column_config={
            "item": st.column_config.TextColumn("Descrição da Despesa Comum"),
            "valor": st.column_config.NumberColumn("Valor Mensal (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    if st.button("💾 Salvar Despesas Comuns"):
        salvar_comuns(df_comuns_edit)
        st.success("Despesas comuns salvas com sucesso!")
        st.rerun()

with tab_pontuais:
    st.header("💸 Gastos Pontuais em Dinheiro/PIX (Imprevistos do Mês)")
    col_sel_p, _ = st.columns([2, 3])
    with col_sel_p:
        mes_pontual = st.selectbox("Selecione o Mês:", MESES_PROJECAO, index=0)
        
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
    if st.button("💾 Salvar Gastos Pontuais"):
        salvar_pontuais(mes_pontual, df_pontuais_edit)
        st.success(f"Gastos pontuais de {mes_pontual} salvos com sucesso!")
        st.rerun()

with tab_consolidado:
    st.header("🏠 Visão Consolidada, Caixinha & Totais")
    
    st.subheader("📦 Caixinha de Reserva da Família (Acumulativa)")
    df_caixinha_db = carregar_caixinha()
    rows_caixinha = []
    
    for mes in MESES_PROJECAO:
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
    if st.button("💾 Salvar Aportes da Caixinha"):
        salvar_caixinha(df_caixinha_edit)
        st.success("Aportes da caixinha salvos com sucesso!")
        st.rerun()
        
    acumulado = 0.0
    dict_caixinha_acumulado = {}
    dict_caixinha_mes = {}
    for _, row in df_caixinha_edit.iterrows():
        mes = row['Mês']
        val = float(row['Aporte do Mês (R$)']) if pd.notnull(row['Aporte do Mês (R$)']) else 0.0
        acumulado += val
        dict_caixinha_mes[mes] = val
        dict_caixinha_acumulado[mes] = acumulado

    st.divider()

    total_comuns_fixos = df_comuns_edit['valor'].sum() if not df_comuns_edit.empty else 0.0
    df_todos_pontuais = carregar_todos_pontuais()

def extrair_totais_completos():
        prog_p1_sum = carregar_programado_cartao("Pessoa 1")['valor'].sum()
        prog_p2_sum = carregar_programado_cartao("Pessoa 2")['valor'].sum()
        
        totais = {mes: {"rec_p1": 0, "cart_p1": 0, "fixos_p1": fixos_p1['valor'].sum(),
                        "rec_p2": 0, "cart_p2": 0, "fixos_p2": fixos_p2['valor'].sum(),
                        "comuns_fixos": total_comuns_fixos,
                        "pont_p1": 0, "pont_p2": 0, "pont_comum": 0,
                        "caixinha_mes": dict_caixinha_mes.get(mes, 0.0),
                        "caixinha_acum": dict_caixinha_acumulado.get(mes, 0.0)} for mes in MESES_PROJECAO}
        
        for mes in MESES_PROJECAO:
            totais[mes]["rec_p1"] = rec_p1[mes].sum()
            totais[mes]["cart_p1"] = cart_p1[mes].sum() + prog_p1_sum
            totais[mes]["rec_p2"] = rec_p2[mes].sum()
            totais[mes]["cart_p2"] = cart_p2[mes].sum() + prog_p2_sum
            
            if not df_todos_pontuais.empty:
                df_p = df_todos_pontuais[df_todos_pontuais['mes_ano'] == mes]
                totais[mes]["pont_p1"] = df_p[df_p['pessoa'] == 'Pessoa 1']['valor'].sum() if not df_p.empty else 0
                totais[mes]["pont_p2"] = df_p[df_p['pessoa'] == 'Pessoa 2']['valor'].sum() if not df_p.empty else 0
                totais[mes]["pont_comum"] = df_p[df_p['pessoa'] == 'Comum / Casa']['valor'].sum() if not df_p.empty else 0
            
        return totais

    totais_gerais = extrair_totais_completos()

    st.subheader("📅 Projeção Evolutiva Mês a Mês & Total Geral")
    
    row_rec = {"Métrica": "1. Renda Total Família"}
    row_p1 = {"Métrica": "2. Gastos Próprios - Pessoa 1"}
    row_p2 = {"Métrica": "3. Gastos Próprios - Pessoa 2"}
    row_comum = {"Métrica": "4. Despesas Comuns (Casa/Aluguel)"}
    row_caixinha_m = {"Métrica": "5. Aporte Caixinha (Mês)"}
    row_desp_t = {"Métrica": "6. Despesa Total Família + Caixinha"}
    row_sobra = {"Métrica": "7. Sobra Líquida do Mês"}
    row_caixinha_a = {"Métrica": "8. Caixinha Saldo Acumulado"}
    
    tot_rec_g, tot_desp_g = 0, 0
    
    for mes in MESES_PROJECAO:
        tg = totais_gerais[mes]
        rf = tg["rec_p1"] + tg["rec_p2"]
        dp1 = tg["cart_p1"] + tg["fixos_p1"] + tg["pont_p1"] + prov_din_p1_df['valor'].sum()
        dp2 = tg["cart_p2"] + tg["fixos_p2"] + tg["pont_p2"] + prov_din_p2_df['valor'].sum()
        dcom = tg["comuns_fixos"] + tg["pont_comum"]
        c_m = tg["caixinha_mes"]
        df_total = dp1 + dp2 + dcom + c_m
        sf = rf - df_total
        
        row_rec[mes] = rf
        row_p1[mes] = dp1
        row_p2[mes] = dp2
        row_comum[mes] = dcom
        row_caixinha_m[mes] = c_m
        row_desp_t[mes] = df_total
        row_sobra[mes] = sf
        row_caixinha_a[mes] = tg["caixinha_acum"]
        
        tot_rec_g += rf
        tot_desp_g += df_total
        
    row_rec["TOTAL GERAL"] = tot_rec_g
    row_p1["TOTAL GERAL"] = sum(totais_gerais[m]["cart_p1"] + totais_gerais[m]["fixos_p1"] + totais_gerais[m]["pont_p1"] for m in MESES_PROJECAO) + (prov_din_p1_df['valor'].sum() * len(MESES_PROJECAO))
    row_p2["TOTAL GERAL"] = sum(totais_gerais[m]["cart_p2"] + totais_gerais[m]["fixos_p2"] + totais_gerais[m]["pont_p2"] for m in MESES_PROJECAO) + (prov_din_p2_df['valor'].sum() * len(MESES_PROJECAO))
    row_comum["TOTAL GERAL"] = sum(totais_gerais[m]["comuns_fixos"] + totais_gerais[m]["pont_comum"] for m in MESES_PROJECAO)
    row_caixinha_m["TOTAL GERAL"] = sum(totais_gerais[m]["caixinha_mes"] for m in MESES_PROJECAO)
    row_desp_t["TOTAL GERAL"] = tot_desp_g
    row_sobra["TOTAL GERAL"] = tot_rec_g - tot_desp_g
    row_caixinha_a["TOTAL GERAL"] = dict_caixinha_acumulado[MESES_PROJECAO[-1]]

    df_resumo = pd.DataFrame([
        row_rec, row_p1, row_p2, row_comum, row_caixinha_m, row_desp_t, row_sobra, row_caixinha_a
    ])
    
    cols_conf = {mes: st.column_config.NumberColumn(format="R$ %.2f") for mes in MESES_PROJECAO}
    cols_conf["TOTAL GERAL"] = st.column_config.NumberColumn("TOTAL GERAL PERÍODO", format="R$ %.2f")

    st.dataframe(df_resumo, use_container_width=True, column_config=cols_conf)
