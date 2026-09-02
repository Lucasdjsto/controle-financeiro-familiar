import os
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# 1. Configuração da Página
st.set_page_config(page_title="Sistema Integrado de Gestão Financeira", layout="wide")

# 2. Injeção de CSS para Tabelas Compactas e Layout Fluido
st.markdown("""
    <style>
        .block-container {
            padding-top: 0.8rem !important;
            padding-bottom: 1.2rem !important;
            padding-left: 0.6rem !important;
            padding-right: 0.6rem !important;
        }
        
        [data-testid="stDataFrame"] div, [data-testid="stDataEditor"] div {
            font-size: 0.82rem !important;
        }
        
        .stDataFrame [data-testid="stTable"] td, .stDataFrame [data-testid="stTable"] th {
            padding: 2px 6px !important;
        }
        
        .metrics-container {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            width: 100%;
            margin-bottom: 0.6rem;
        }
        
        .metric-card {
            background-color: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 10px 12px;
            flex: 1 1 calc(20% - 10px);
            min-width: 160px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }

        .metric-card-sub {
            background-color: #0f172a;
            border: 1px dashed #475569;
            border-radius: 8px;
            padding: 8px 10px;
            flex: 1 1 calc(25% - 10px);
            min-width: 150px;
        }
        
        .metric-label {
            font-size: 0.78rem;
            color: #94a3b8;
            margin-bottom: 2px;
            font-weight: 500;
        }
        
        .metric-value {
            font-size: 1.15rem;
            font-weight: 700;
            color: #f8fafc;
        }
        
        .delta-positive { color: #4ade80; font-size: 0.75rem; font-weight: 600; }
        .delta-negative { color: #f87171; font-size: 0.75rem; font-weight: 600; }

        .stButton > button {
            border-radius: 6px;
            font-weight: 600;
            padding: 4px 12px;
            font-size: 0.85rem;
        }

        @media (max-width: 1024px) {
            .metric-card, .metric-card-sub { flex: 1 1 calc(33.33% - 10px); }
        }
        @media (max-width: 640px) {
            .metric-card, .metric-card-sub { flex: 1 1 100%; }
            .metric-value { font-size: 1.1rem; }
        }
    </style>
""", unsafe_allow_html=True)

# Helper seguro para conversão de números
def safe_float(val, default=0.0):
    try:
        if pd.isna(val) or val is None or str(val).strip() == "":
            return default
        return float(val)
    except (ValueError, TypeError):
        return default

# 3. Autenticação por Senha (Fixada em pretabebe)
def verificar_senha():
    if "autenticado" not in st.session_state:
        st.session_state["autenticado"] = False

    if st.session_state["autenticado"]:
        return True

    st.title("🔒 Acesso Restrito - Gestão Financeira")
    
    with st.form("form_login"):
        senha_digitada = st.text_input("Digite a senha de acesso:", type="password")
        botao_entrar = st.form_submit_button("Entrar")
        
        if botao_entrar:
            if senha_digitada == "pretabebe":
                st.session_state["autenticado"] = True
                st.success("Acesso liberado!")
                st.rerun()
            else:
                st.error("Senha incorreta! Tente novamente.")
    return False

if not verificar_senha():
    st.stop()

# 4. Conexão Otimizada com Pooler do Supabase
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
        pool_size=3,
        max_overflow=2,
        pool_recycle=300,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 10}
    )

engine = get_db_engine()

# 5. Inicialização das Tabelas no Banco
def init_db():
    try:
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
                    valor DOUBLE PRECISION DEFAULT 0,
                    pagador TEXT DEFAULT 'Dividido (50/50)'
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
                CREATE TABLE IF NOT EXISTS status_faturas (
                    pessoa TEXT,
                    mes_ano TEXT,
                    fechada BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (pessoa, mes_ano)
                );
            '''))
    except Exception as e:
        st.error(f"Erro de Conexão com o Banco de Dados: {e}")

init_db()

# 6. GERADOR DINÂMICO DE MESES E ESTRUTURAS
def gerar_linha_tempo_dinamica(mes_inicio_str="08.2026", quantidade_meses=36):
    m_init, y_init = map(int, mes_inicio_str.split("."))
    meses = []
    curr_m, curr_y = m_init, y_init
    for _ in range(quantidade_meses):
        meses.append(f"{curr_m:02d}.{curr_y}")
        curr_m += 1
        if curr_m > 12:
            curr_m = 1
            curr_y += 1
    return meses

TODOS_MESES_SISTEMA = gerar_linha_tempo_dinamica("08.2026", 48)

ESTRUTURA_CARTÕES = {
    "Pessoa 1": ["C6 Carbon", "Nubank", "Santander"],
    "Pessoa 2": ["Banco do Brasil", "Rico", "C6", "Amazon"]
}

ESTRUTURA_RECEITAS = {
    "Pessoa 1": ["Salário Base", "Receita Extra"],
    "Pessoa 2": ["Salário Base", "Receita Extra"]
}

# 7. Funções de Leitura Otimizadas em Lote (Cache de 5 minutos)
@st.cache_data(ttl=300)
def carregar_dados_globais():
    with engine.connect() as conn:
        df_proj = pd.read_sql(text("SELECT * FROM projecao"), conn)
        df_fixos = pd.read_sql(text("SELECT * FROM gastos_fixos"), conn)
        df_comuns = pd.read_sql(text("SELECT * FROM gastos_comuns"), conn)
        df_pontuais = pd.read_sql(text("SELECT * FROM pontuais_dinheiro"), conn)
        df_caixinha = pd.read_sql(text("SELECT * FROM caixinha"), conn)
        df_prog = pd.read_sql(text("SELECT * FROM programado_cartao"), conn)
        df_status = pd.read_sql(text("SELECT * FROM status_faturas"), conn)
    
    if 'pagador' not in df_comuns.columns:
        df_comuns['pagador'] = 'Dividido (50/50)'
        
    return df_proj, df_fixos, df_comuns, df_pontuais, df_caixinha, df_prog, df_status

df_proj_all, df_fixos_all, df_comuns_all, df_pontuais_all, df_caixinha_all, df_prog_all, df_status_all = carregar_dados_globais()

def get_projecao(pessoa, tipo):
    if df_proj_all.empty:
        return pd.DataFrame(columns=['pessoa', 'tipo', 'item', 'mes_ano', 'valor'])
    return df_proj_all[(df_proj_all['pessoa'] == pessoa) & (df_proj_all['tipo'] == tipo)]

def get_fixos(pessoa):
    if df_fixos_all.empty:
        return pd.DataFrame(columns=['id', 'item', 'valor'])
    return df_fixos_all[df_fixos_all['pessoa'] == pessoa][['id', 'item', 'valor']]

def get_programado_cartao(pessoa):
    if df_prog_all.empty:
        return pd.DataFrame(columns=['id', 'cartao', 'descricao', 'valor'])
    return df_prog_all[df_prog_all['pessoa'] == pessoa][['id', 'cartao', 'descricao', 'valor']]

# 8. Funções de Escrita
def salvar_projecao(pessoa, tipo, df_editado, meses_visiveis):
    with engine.begin() as conn:
        for _, row in df_editado.iterrows():
            item = str(row['Item'])
            for mes in meses_visiveis:
                val = safe_float(row[mes])
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
                conn.execute(text(query), {"pessoa": pessoa, "item": str(row['item']), "val": safe_float(row['valor'])})

def salvar_comuns(df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gastos_comuns"))
        for _, row in df_editado.iterrows():
            if str(row['item']).strip():
                pag = str(row.get('pagador', 'Dividido (50/50)'))
                query = "INSERT INTO gastos_comuns (item, valor, pagador) VALUES (:item, :val, :pag)"
                conn.execute(text(query), {"item": str(row['item']), "val": safe_float(row['valor']), "pag": pag})

def salvar_status_fatura(pessoa, mes_ano, fechada):
    with engine.begin() as conn:
        query = '''
            INSERT INTO status_faturas (pessoa, mes_ano, fechada)
            VALUES (:pessoa, :mes_ano, :fechada)
            ON CONFLICT (pessoa, mes_ano)
            DO UPDATE SET fechada = EXCLUDED.fechada;
        '''
        conn.execute(text(query), {"pessoa": pessoa, "mes_ano": mes_ano, "fechada": fechada})

def resetar_todos_status_faturas():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM status_faturas;"))
    st.cache_data.clear()

def inserir_gasto_rapido(mes_ano, pessoa, descricao, categoria, valor):
    with engine.begin() as conn:
        query = '''
            INSERT INTO pontuais_dinheiro (mes_ano, pessoa, descricao, categoria, valor)
            VALUES (:mes_ano, :pessoa, :descricao, :categoria, :valor)
        '''
        conn.execute(text(query), {
            "mes_ano": mes_ano,
            "pessoa": pessoa,
            "descricao": descricao,
            "categoria": categoria,
            "valor": safe_float(valor)
        })
    st.cache_data.clear()

def deletar_gasto_pontual(gasto_id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM pontuais_dinheiro WHERE id = :id"), {"id": gasto_id})
    st.cache_data.clear()

def salvar_caixinha(df_editado):
    with engine.begin() as conn:
        for _, row in df_editado.iterrows():
            mes = row['Mês']
            val = safe_float(row['Aporte do Mês (R$)'])
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
            if pd.notnull(row.get('descricao')) and str(row['descricao']).strip():
                cartao_val = str(row['cartao']) if pd.notnull(row.get('cartao')) else ESTRUTURA_CARTÕES[pessoa][0]
                desc_val = str(row['descricao'])
                val_val = safe_float(row.get('valor'))
                query = "INSERT INTO programado_cartao (pessoa, cartao, descricao, valor) VALUES (:pessoa, :cartao, :desc, :val)"
                conn.execute(text(query), {"pessoa": pessoa, "cartao": cartao_val, "desc": desc_val, "val": val_val})

# 9. LÓGICA DE CÁLCULO FINANCEIRO OTIMIZADA
def calcular_sequencia_financeira():
    prog_p1 = get_programado_cartao("Pessoa 1")['valor'].apply(safe_float).sum() if not df_prog_all.empty else 0.0
    prog_p2 = get_programado_cartao("Pessoa 2")['valor'].apply(safe_float).sum() if not df_prog_all.empty else 0.0
    
    fix_p1 = get_fixos("Pessoa 1")['valor'].apply(safe_float).sum() if not df_fixos_all.empty else 0.0
    fix_p2 = get_fixos("Pessoa 2")['valor'].apply(safe_float).sum() if not df_fixos_all.empty else 0.0
    
    comuns_val_total = df_comuns_all['valor'].apply(safe_float).sum() if not df_comuns_all.empty else 0.0
    comuns_p1 = df_comuns_all[df_comuns_all['pagador'] == 'Pessoa 1']['valor'].apply(safe_float).sum() if not df_comuns_all.empty else 0.0
    comuns_p2 = df_comuns_all[df_comuns_all['pagador'] == 'Pessoa 2']['valor'].apply(safe_float).sum() if not df_comuns_all.empty else 0.0
    comuns_div = df_comuns_all[df_comuns_all['pagador'] == 'Dividido (50/50)']['valor'].apply(safe_float).sum() if not df_comuns_all.empty else 0.0
    
    tot_fixos = fix_p1 + fix_p2 + comuns_val_total

    dados_meses = {}
    saldo_acumulado_anterior = 0.0

    for m in TODOS_MESES_SISTEMA:
        r_p1 = df_proj_all[(df_proj_all['mes_ano'] == m) & (df_proj_all['pessoa'] == 'Pessoa 1') & (df_proj_all['tipo'] == 'RECEITA')]['valor'].apply(safe_float).sum() if not df_proj_all.empty else 0.0
        r_p2 = df_proj_all[(df_proj_all['mes_ano'] == m) & (df_proj_all['pessoa'] == 'Pessoa 2') & (df_proj_all['tipo'] == 'RECEITA')]['valor'].apply(safe_float).sum() if not df_proj_all.empty else 0.0
        renda_mes = r_p1 + r_p2

        c_p1 = df_proj_all[(df_proj_all['mes_ano'] == m) & (df_proj_all['pessoa'] == 'Pessoa 1') & (df_proj_all['tipo'] == 'CARTAO')]['valor'].apply(safe_float).sum() if not df_proj_all.empty else 0.0
        c_p2 = df_proj_all[(df_proj_all['mes_ano'] == m) & (df_proj_all['pessoa'] == 'Pessoa 2') & (df_proj_all['tipo'] == 'CARTAO')]['valor'].apply(safe_float).sum() if not df_proj_all.empty else 0.0
        
        f1_fechada = False
        f2_fechada = False
        if not df_status_all.empty:
            st1 = df_status_all[(df_status_all['pessoa'] == 'Pessoa 1') & (df_status_all['mes_ano'] == m)]
            f1_fechada = bool(st1['fechada'].iloc[0]) if not st1.empty else False
            st2 = df_status_all[(df_status_all['pessoa'] == 'Pessoa 2') & (df_status_all['mes_ano'] == m)]
            f2_fechada = bool(st2['fechada'].iloc[0]) if not st2.empty else False

        add_prog_p1 = 0.0 if f1_fechada else prog_p1
        add_prog_p2 = 0.0 if f2_fechada else prog_p2

        p_df = df_pontuais_all[df_pontuais_all['mes_ano'] == m] if not df_pontuais_all.empty else pd.DataFrame()
        pont_p1 = p_df[p_df['pessoa'] == 'Pessoa 1']['valor'].apply(safe_float).sum() if not p_df.empty else 0.0
        pont_p2 = p_df[p_df['pessoa'] == 'Pessoa 2']['valor'].apply(safe_float).sum() if not p_df.empty else 0.0
        pont_comum = p_df[p_df['pessoa'] == 'Comum / Casa']['valor'].apply(safe_float).sum() if not p_df.empty else 0.0
        pontual_mes = pont_p1 + pont_p2 + pont_comum

        gasto_exclusivo_p1 = (c_p1 + add_prog_p1) + fix_p1 + pont_p1 + comuns_p1 + (comuns_div / 2)
        gasto_exclusivo_p2 = (c_p2 + add_prog_p2) + fix_p2 + pont_p2 + comuns_p2 + (comuns_div / 2)

        caixinha_mes = df_caixinha_all[df_caixinha_all['mes_ano'] == m]['valor'].apply(safe_float).sum() if not df_caixinha_all.empty else 0.0

        saidas_mes = (c_p1 + c_p2 + add_prog_p1 + add_prog_p2) + tot_fixos + pontual_mes + caixinha_mes
        sobra_do_mes_bruta = renda_mes - saidas_mes
        
        saldo_conta_final = saldo_acumulado_anterior + sobra_do_mes_bruta

        dados_meses[m] = {
            "saldo_anterior": saldo_acumulado_anterior,
            "renda_mes": renda_mes,
            "renda_p1": r_p1,
            "renda_p2": r_p2,
            "gasto_p1": gasto_exclusivo_p1,
            "gasto_p2": gasto_exclusivo_p2,
            "saidas_mes": saidas_mes,
            "caixinha_mes": caixinha_mes,
            "sobra_mes_isolada": sobra_do_mes_bruta,
            "saldo_acumulado_final": saldo_conta_final
        }

        saldo_acumulado_anterior = saldo_conta_final

    return dados_meses

dados_financeiros = calcular_sequencia_financeira()

# 10. CABEÇALHO E CONTROLES
col_head, col_save_btn, col_logout_btn = st.columns([7, 3, 1.5])
with col_head:
    st.title("📊 Painel Financeiro Integrado")

with col_save_btn:
    st.write("")
    if st.button("💾 SALVAR ALTERAÇÕES", type="primary", use_container_width=True):
        if "rec_p1_df" in st.session_state: salvar_projecao("Pessoa 1", "RECEITA", st.session_state["rec_p1_df"], st.session_state["meses_v"])
        if "cart_p1_df" in st.session_state: salvar_projecao("Pessoa 1", "CARTAO", st.session_state["cart_p1_df"], st.session_state["meses_v"])
        if "fix_p1_df" in st.session_state: salvar_fixos("Pessoa 1", st.session_state["fix_p1_df"])
        if "prog_p1_df" in st.session_state: salvar_programado_cartao("Pessoa 1", st.session_state["prog_p1_df"])

        if "rec_p2_df" in st.session_state: salvar_projecao("Pessoa 2", "RECEITA", st.session_state["rec_p2_df"], st.session_state["meses_v"])
        if "cart_p2_df" in st.session_state: salvar_projecao("Pessoa 2", "CARTAO", st.session_state["cart_p2_df"], st.session_state["meses_v"])
        if "fix_p2_df" in st.session_state: salvar_fixos("Pessoa 2", st.session_state["fix_p2_df"])
        if "prog_p2_df" in st.session_state: salvar_programado_cartao("Pessoa 2", st.session_state["prog_p2_df"])

        if "comuns_df" in st.session_state: salvar_comuns(st.session_state["comuns_df"])
        if "caixinha_df" in st.session_state: salvar_caixinha(st.session_state["caixinha_df"])
        
        st.cache_data.clear()
        st.success("Tudo foi salvo com sucesso!")
        st.rerun()

with col_logout_btn:
    st.write("")
    if st.button("🚪 Sair", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()

# CONTROLES TEMPORAIS
c_sel1, c_sel2, c_reset = st.columns([5, 4, 3])
with c_sel1:
    mes_atual = st.selectbox("📅 Selecione o Mês Atual de Trabalho (Arquiva Anteriores):", TODOS_MESES_SISTEMA[:24], index=0)
    st.session_state["mes_atual_sel"] = mes_atual
with c_sel2:
    modo_exibicao = st.radio("🔍 Horizonte Futuro:", ["6 Meses", "12 Meses"], index=0, horizontal=True)
with c_reset:
    st.write("")
    if st.button("🔄 Resetar Status Faturas", help="Limpa do banco todos os status de Fatura Fechada acumulados"):
        resetar_todos_status_faturas()
        st.success("Status de faturas resetados no banco!")
        st.rerun()

idx_foco = TODOS_MESES_SISTEMA.index(mes_atual)
qtd_meses = 6 if modo_exibicao == "6 Meses" else 12

meses_visiveis = TODOS_MESES_SISTEMA[idx_foco:idx_foco + qtd_meses]
st.session_state["meses_v"] = meses_visiveis

d_foco = dados_financeiros[mes_atual]

# EXPANDER DE GASTO RÁPIDO
with st.expander("➕ **Registrar Novo Gasto Rápido (PIX / Dinheiro)**", expanded=False):
    with st.form("form_gasto_rapido_exp", clear_on_submit=True):
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            desc = st.text_input("Descrição (ex: Barbeiro, Feira, Farmácia)", placeholder="Digite a descrição...")
            val = st.number_input("Valor (R$)", min_value=0.01, step=5.0, format="%.2f")
        with c_f2:
            pessoa = st.selectbox("Quem Pagou?", ["Pessoa 1", "Pessoa 2", "Comum / Casa"])
            cat = st.selectbox("Categoria", ["Mercado / Feira", "Barbeiro / Estética", "Lazer / Restaurante", "Transporte", "Farmácia", "Outros"])
            
        mes_target = st.selectbox("Mês de Referência", TODOS_MESES_SISTEMA[:24], index=TODOS_MESES_SISTEMA.index(mes_atual))
        btn_salvar_gasto = st.form_submit_button("💾 Salvar Gasto", type="primary", use_container_width=True)
        
        if btn_salvar_gasto:
            if not desc.strip():
                st.error("Por favor, preencha a descrição do gasto.")
            else:
                inserir_gasto_rapido(mes_target, pessoa, desc, cat, val)
                st.success("Gasto registrado com sucesso!")
                st.rerun()

# PAINEL RESUMO MENSAL
st.markdown(f"#### ⚡ Resumo Financeiro Consolidador - {mes_atual}")

s_final = d_foco['saldo_acumulado_final']
delta_class = "delta-positive" if s_final >= 0 else "delta-negative"
delta_label = "↑ Positivo" if s_final >= 0 else "↓ Déficit"

st.markdown(f"""
    <div class="metrics-container">
        <div class="metric-card">
            <div class="metric-label">1. Saldo Inicial em Conta</div>
            <div class="metric-value">R$ {d_foco['saldo_anterior']:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">2. Renda Total Família</div>
            <div class="metric-value">R$ {d_foco['renda_mes']:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">3. Saídas Totais (Geral)</div>
            <div class="metric-value">R$ {d_foco['saidas_mes']:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">4. Aporte Caixinha</div>
            <div class="metric-value">R$ {d_foco['caixinha_mes']:,.2f}</div>
        </div>
        <div class="metric-card">
            <div class="metric-label">5. Saldo Acumulado Final</div>
            <div class="metric-value">R$ {s_final:,.2f}</div>
            <div class="{delta_class}">{delta_label}</div>
        </div>
    </div>
    
    <div class="metrics-container">
        <div class="metric-card-sub">
            <div class="metric-label">👤 Pessoa 1 (Lucas) - Renda</div>
            <div class="metric-value" style="color:#60a5fa;">R$ {d_foco['renda_p1']:,.2f}</div>
        </div>
        <div class="metric-card-sub">
            <div class="metric-label">👤 Pessoa 1 (Lucas) - Gastos Próprios</div>
            <div class="metric-value" style="color:#f87171;">R$ {d_foco['gasto_p1']:,.2f}</div>
        </div>
        <div class="metric-card-sub">
            <div class="metric-label">👤 Pessoa 2 (Marcella) - Renda</div>
            <div class="metric-value" style="color:#60a5fa;">R$ {d_foco['renda_p2']:,.2f}</div>
        </div>
        <div class="metric-card-sub">
            <div class="metric-label">👤 Pessoa 2 (Marcella) - Gastos Próprios</div>
            <div class="metric-value" style="color:#f87171;">R$ {d_foco['gasto_p2']:,.2f}</div>
        </div>
    </div>
""", unsafe_allow_html=True)

st.divider()

# 11. Interface Principal
tab_p1, tab_p2, tab_comuns, tab_consolidado = st.tabs([
    "👤 Pessoa 1 (Lucas)", 
    "👤 Pessoa 2 (Marcella)", 
    "🏡 Despesas Comuns (Casa/Aluguel)",
    "🏠 Visão Consolidada & Caixinha"
])

def renderizar_pessoa(pessoa, p_code):
    st.subheader("💵 1. Receitas (Salário e Rendimentos)")
    df_rec_db = get_projecao(pessoa, "RECEITA")
    rows_rec = []
    for item in ESTRUTURA_RECEITAS[pessoa]:
        row_dict = {"Item": item}
        for mes in meses_visiveis:
            val = df_rec_db[(df_rec_db['item'] == item) & (df_rec_db['mes_ano'] == mes)]['valor']
            row_dict[mes] = safe_float(val.iloc[0]) if not val.empty else 0.0
        rows_rec.append(row_dict)
    
    df_rec_grid = pd.DataFrame(rows_rec)
    df_rec_edit = st.data_editor(
        df_rec_grid, num_rows="fixed", use_container_width=True, key=f"rec_{p_code}", height=120,
        column_config={mes: st.column_config.NumberColumn(f"{mes}", format="R$ %.2f", min_value=0.0) for mes in meses_visiveis}
    )
    st.session_state[f"rec_{p_code}_df"] = df_rec_edit

    st.divider()

    st.subheader("💳 2. Evolução das Faturas de Cartão de Crédito")
    
    st_match = df_status_all[(df_status_all['pessoa'] == pessoa) & (df_status_all['mes_ano'] == mes_atual)] if not df_status_all.empty else pd.DataFrame()
    is_closed_db = bool(st_match['fechada'].iloc[0]) if not st_match.empty else False
    
    key_chk = f"chk_fat_{p_code}_{mes_atual}"
    if key_chk not in st.session_state:
        st.session_state[key_chk] = is_closed_db

    chk_fechada = st.checkbox(
        f"✅ Fatura de {mes_atual} Fechada / Processada (Desliga Provisões de {pessoa})", 
        key=key_chk
    )
    
    if chk_fechada != is_closed_db:
        salvar_status_fatura(pessoa, mes_atual, chk_fechada)
        st.cache_data.clear()
        st.rerun()

    df_cart_db = get_projecao(pessoa, "CARTAO")
    rows_cart = []
    for item in ESTRUTURA_CARTÕES[pessoa]:
        row_dict = {"Item": item}
        for mes in meses_visiveis:
            val = df_cart_db[(df_cart_db['item'] == item) & (df_cart_db['mes_ano'] == mes)]['valor']
            row_dict[mes] = safe_float(val.iloc[0]) if not val.empty else 0.0
        rows_cart.append(row_dict)
        
    df_cart_grid = pd.DataFrame(rows_cart)
    df_cart_edit = st.data_editor(
        df_cart_grid, num_rows="fixed", use_container_width=True, key=f"cart_{p_code}", height=170,
        column_config={mes: st.column_config.NumberColumn(f"{mes}", format="R$ %.2f", min_value=0.0) for mes in meses_visiveis}
    )
    st.session_state[f"cart_{p_code}_df"] = df_cart_edit

    st.divider()

    st.subheader("🔮 3. Lançamentos Programados no Cartão (Seguros / Assinaturas Futuras)")
    df_prog_cart = get_programado_cartao(pessoa)
    df_prog_edit = st.data_editor(
        df_prog_cart, num_rows="dynamic", use_container_width=True, key=f"prog_{p_code}", height=150,
        column_config={
            "cartao": st.column_config.SelectboxColumn("Cartão", options=ESTRUTURA_CARTÕES[pessoa]),
            "descricao": st.column_config.TextColumn("Descrição (ex: Seguro, Netflix)"),
            "valor": st.column_config.NumberColumn("Valor Previsto (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    st.session_state[f"prog_{p_code}_df"] = df_prog_edit

    st.divider()

    st.subheader("📌 4. Gastos Fixos Individuais Recorrentes")
    df_fixos_db = get_fixos(pessoa)
    df_fixos_edit = st.data_editor(
        df_fixos_db, num_rows="dynamic", use_container_width=True, key=f"fix_{p_code}", height=150,
        column_config={
            "item": st.column_config.TextColumn("Descrição do Gasto Fixo Individual"),
            "valor": st.column_config.NumberColumn("Valor Mensal (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    st.session_state[f"fix_{p_code}_df"] = df_fixos_edit

    st.divider()

    st.subheader("💸 5. Extrato de Gastos Esporádicos (PIX / Dinheiro)")
    pontuais_p = df_pontuais_all[(df_pontuais_all['pessoa'] == pessoa) & (df_pontuais_all['mes_ano'] == mes_atual)] if not df_pontuais_all.empty else pd.DataFrame()
    
    if not pontuais_p.empty:
        for _, g in pontuais_p.iterrows():
            c_g1, c_g2, c_g3, c_g4 = st.columns([4, 3, 3, 1])
            c_g1.write(f"**{g['descricao']}**")
            c_g2.write(f"🏷️ {g['categoria']}")
            c_g3.write(f"**R$ {safe_float(g['valor']):,.2f}**")
            if c_g4.button("🗑️", key=f"del_{g['id']}"):
                deletar_gasto_pontual(g['id'])
                st.rerun()
    else:
        st.info("Nenhum gasto em PIX/dinheiro registrado para este mês.")

with tab_p1:
    renderizar_pessoa("Pessoa 1", "p1")

with tab_p2:
    renderizar_pessoa("Pessoa 2", "p2")

with tab_comuns:
    st.header("🏡 Despesas Comuns do Casal / Casa")
    df_comuns_edit = st.data_editor(
        df_comuns_all, num_rows="dynamic", use_container_width=True, key="comuns_editor", height=220,
        column_config={
            "item": st.column_config.TextColumn("Descrição da Despesa Comum"),
            "valor": st.column_config.NumberColumn("Valor Mensal (R$)", format="R$ %.2f", min_value=0.0),
            "pagador": st.column_config.SelectboxColumn("Responsável pelo Pagamento", options=["Pessoa 1", "Pessoa 2", "Dividido (50/50)"])
        }
    )
    st.session_state["comuns_df"] = df_comuns_edit

with tab_consolidado:
    st.header("🏠 Visão Consolidada, Caixinha & Totais")
    
    st.subheader("📦 Caixinha de Reserva da Família (Acumulativa)")
    rows_caixinha = []
    acumulado_temp = 0.0
    for mes in meses_visiveis:
        val = df_caixinha_all[df_caixinha_all['mes_ano'] == mes]['valor'] if not df_caixinha_all.empty else pd.Series()
        val_aporte = safe_float(val.iloc[0]) if not val.empty else 0.0
        acumulado_temp += val_aporte
        rows_caixinha.append({
            "Mês": mes, 
            "Aporte do Mês (R$)": val_aporte,
            "Total Acumulado na Caixinha (R$)": acumulado_temp
        })
        
    df_caixinha_grid = pd.DataFrame(rows_caixinha)
    df_caixinha_edit = st.data_editor(
        df_caixinha_grid, num_rows="fixed", use_container_width=True, key="caixinha_editor", height=200,
        column_config={
            "Mês": st.column_config.TextColumn("Mês", disabled=True),
            "Aporte do Mês (R$)": st.column_config.NumberColumn("Aporte do Mês (R$)", format="R$ %.2f", min_value=0.0),
            "Total Acumulado na Caixinha (R$)": st.column_config.NumberColumn("Total Acumulado na Caixinha (R$)", format="R$ %.2f", disabled=True)
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
    st.dataframe(df_resumo, use_container_width=True, column_config=cols_conf, height=220)
