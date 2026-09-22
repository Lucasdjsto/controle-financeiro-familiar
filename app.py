import os
import urllib.parse
from datetime import datetime
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# 1. Configuração da Página
st.set_page_config(
    page_title="Gestão Financeira Familiar",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. CSS Customizado - Identidade Visual Familiar (Tema Blue/Indigo)
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"] {
            font-family: 'Plus Jakarta Sans', sans-serif !important;
        }

        .stApp {
            background-color: #0b0f19 !important;
        }

        .block-container {
            padding-top: 1.8rem !important;
            padding-bottom: 1.5rem !important;
            padding-left: 0.8rem !important;
            padding-right: 0.8rem !important;
        }
        
        .hero-banner-fam {
            background: linear-gradient(135deg, #1e3a8a 0%, #1e1b4b 100%);
            border: 1px solid #3b82f6;
            border-radius: 12px;
            padding: 12px 18px;
            margin-bottom: 15px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 20px rgba(59, 130, 246, 0.15);
        }

        .hero-title-fam {
            font-size: 1.25rem;
            font-weight: 800;
            color: #eff6ff;
            letter-spacing: -0.02em;
            margin: 0;
        }

        .hero-badge-fam {
            background-color: #3b82f6;
            color: #ffffff;
            font-size: 0.68rem;
            font-weight: 800;
            padding: 4px 10px;
            border-radius: 20px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .section-header-fam {
            font-size: 0.78rem;
            font-weight: 800;
            color: #60a5fa;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            margin: 14px 0 8px 0;
            display: flex;
            align-items: center;
            gap: 6px;
        }
        
        .grid-sec1 {
            display: grid;
            grid-template-columns: repeat(1, 1fr);
            gap: 10px;
            margin-bottom: 12px;
        }
        
        .grid-sec2 {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin-bottom: 12px;
        }

        .card-base-fam {
            background: #111827;
            border: 1px solid #1f2937;
            border-left: 4px solid #3b82f6;
            border-radius: 10px;
            padding: 12px 14px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            min-height: 80px;
            box-sizing: border-box;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }
        
        .card-base-fam:hover {
            border-color: #60a5fa;
        }

        .card-saldo-ini { border-left-color: #6366f1; }
        .card-disp { border-left-color: #38bdf8; }
        .card-previsto { 
            background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%);
            border: 1px solid #6366f1;
            border-left: 4px solid #818cf8;
        }

        .card-receita { border-left-color: #10b981; }
        .card-despesa { border-left-color: #f43f5e; }
        .card-sobra { border-left-color: #f59e0b; background: #181e29; }
        .card-reserva { border-left-color: #0284c7; background: #0c1a29; }
        .card-patrimonio { border-left-color: #8b5cf6; background: #1e1b2e; }

        .card-title-fam { 
            font-size: 0.70rem; 
            color: #9ca3af; 
            font-weight: 700;
            line-height: 1.2;
            margin-bottom: 4px;
            text-transform: uppercase;
        }

        .card-val-fam { 
            font-size: 1.15rem; 
            font-weight: 800; 
            color: #f9fafb; 
            line-height: 1.1;
        }

        .stTabs [data-baseweb="tab-list"] {
            gap: 6px;
            background-color: #111827;
            padding: 5px;
            border-radius: 10px;
            border: 1px solid #1f2937;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 38px;
            border-radius: 7px;
            color: #9ca3af;
            font-weight: 700;
            font-size: 0.82rem;
        }
        
        .stTabs [aria-selected="true"] {
            background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
            color: #ffffff !important;
            box-shadow: 0 2px 10px rgba(37, 99, 235, 0.3);
        }

        .stButton > button {
            border-radius: 7px;
            font-weight: 700;
            padding: 5px 12px;
            font-size: 0.8rem;
            background-color: #1f2937;
            color: #e5e7eb;
            border: 1px solid #374151;
            transition: all 0.2s;
        }

        .stButton > button:hover {
            border-color: #60a5fa;
            color: #60a5fa;
        }

        [data-testid="stDataFrame"] div, [data-testid="stDataEditor"] div {
            font-size: 0.80rem !important;
        }

        @media (min-width: 768px) {
            .grid-sec1 { grid-template-columns: repeat(3, 1fr); }
            .grid-sec2 { grid-template-columns: repeat(3, 1fr); }
        }
    </style>
""", unsafe_allow_html=True)

def safe_float(val, default=0.0):
    try:
        if pd.isna(val) or val is None or str(val).strip() == "":
            return default
        return float(val)
    except (ValueError, TypeError):
        return default

def mes_banco_para_tela(mes_banco):
    try:
        m, y = map(int, mes_banco.split("."))
        m += 1
        if m > 12:
            m = 1
            y += 1
        return f"{m:02d}.{y}"
    except:
        return mes_banco

def mes_tela_para_banco(mes_tela):
    try:
        m, y = map(int, mes_tela.split("."))
        m -= 1
        if m < 1:
            m = 12
            y -= 1
        return f"{m:02d}.{y}"
    except:
        return mes_tela

# 3. Autenticação Familiar
def verificar_senha():
    if "autenticado_fam" not in st.session_state:
        st.session_state["autenticado_fam"] = False

    if st.session_state["autenticado_fam"]:
        return True

    st.markdown("""
        <div style='text-align: center; padding: 40px 20px;'>
            <h2 style='color: #60a5fa;'>🏠 Gestão Financeira Familiar</h2>
            <p style='color: #9ca3af; font-size: 0.9rem;'>Digite a senha de acesso para visualizar e gerir o orçamento da família.</p>
        </div>
    """, unsafe_allow_html=True)
    
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        with st.form("form_login_fam"):
            senha_digitada = st.text_input("Senha de Acesso Familiar:", type="password", placeholder="••••••••")
            botao_entrar = st.form_submit_button("Acessar Painel Familiar", use_container_width=True)
            
            if botao_entrar:
                if senha_digitada == "Lucas@338035":
                    st.session_state["autenticado_fam"] = True
                    st.success("Autenticado com sucesso!")
                    st.rerun()
                else:
                    st.error("Senha incorreta!")
    return False

if not verificar_senha():
    st.stop()

# 4. Conexão com Supabase
@st.cache_resource
def get_db_engine():
    pg_secrets = st.secrets.get("postgres", {})
    db_url = pg_secrets.get("url", "")
    
    if not db_url:
        st.error("❌ Configuração 'postgres.url' ausente no secrets.")
        st.stop()
        
    return create_engine(
        db_url,
        pool_size=2,
        max_overflow=3,
        pool_recycle=300,
        pool_pre_ping=True,
        execution_options={"prepare_threshold": None}
    )

engine = get_db_engine()

def init_db():
    try:
        with engine.begin() as conn:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS fam_projecao (
                    tipo TEXT, item TEXT, mes_ano TEXT,
                    valor DOUBLE PRECISION DEFAULT 0,
                    PRIMARY KEY (tipo, item, mes_ano)
                );
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS fam_gastos_fixos (
                    item TEXT, mes_ano TEXT,
                    valor DOUBLE PRECISION DEFAULT 0,
                    PRIMARY KEY (item, mes_ano)
                );
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS fam_pontuais_dinheiro (
                    id SERIAL PRIMARY KEY, mes_ano TEXT, descricao TEXT, categoria TEXT, valor DOUBLE PRECISION DEFAULT 0
                );
            '''))
            # Tabela de Receitas Rápidas Familiares
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS fam_pontuais_receitas (
                    id SERIAL PRIMARY KEY, mes_ano TEXT, descricao TEXT, categoria TEXT, valor DOUBLE PRECISION DEFAULT 0
                );
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS fam_caixinha (
                    mes_ano TEXT PRIMARY KEY, valor DOUBLE PRECISION DEFAULT 0
                );
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS fam_programado_cartao (
                    id SERIAL PRIMARY KEY, cartao TEXT, descricao TEXT, valor DOUBLE PRECISION DEFAULT 0
                );
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS fam_status_faturas (
                    mes_ano TEXT PRIMARY KEY, fechada BOOLEAN DEFAULT FALSE
                );
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS fam_preferencias (
                    chave TEXT PRIMARY KEY, valor TEXT
                );
            '''))
    except Exception as e:
        st.error(f"Erro ao inicializar o banco de dados familiar: {e}")

init_db()

def carregar_ultimo_mes_salvo(default="10.2026"):
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT valor FROM fam_preferencias WHERE chave = 'ultimo_mes'")).fetchone()
            if res and res[0]:
                return res[0]
    except:
        pass
    return default

def salvar_ultimo_mes_banco(mes_tela):
    try:
        with engine.begin() as conn:
            conn.execute(text('''
                INSERT INTO fam_preferencias (chave, valor) VALUES ('ultimo_mes', :mes)
                ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor;
            '''), {"mes": mes_tela})
    except:
        pass

def gerar_linha_tempo_tela(mes_inicio_str="10.2026", quantidade_meses=48):
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

TODOS_MESES_TELA = gerar_linha_tempo_tela("10.2026", 48)

ESTRUTURA_CARTÕES_BASE = ["Cartão Principal Família", "Cartão Secundário Família"]
ESTRUTURA_RECEITAS = ["Renda Principal Família", "Renda Secundária Família", "Outras Rendas"]

@st.cache_data(ttl=60, show_spinner=False)
def carregar_dados_globais():
    try:
        with engine.connect() as conn:
            df_proj = pd.read_sql(text("SELECT * FROM fam_projecao"), conn)
            df_fixos = pd.read_sql(text("SELECT * FROM fam_gastos_fixos"), conn)
            df_pontuais = pd.read_sql(text("SELECT * FROM fam_pontuais_dinheiro"), conn)
            df_rec_pontuais = pd.read_sql(text("SELECT * FROM fam_pontuais_receitas"), conn)
            df_caixinha = pd.read_sql(text("SELECT * FROM fam_caixinha"), conn)
            df_prog = pd.read_sql(text("SELECT * FROM fam_programado_cartao"), conn)
            df_status = pd.read_sql(text("SELECT * FROM fam_status_faturas"), conn)
            
        return df_proj, df_fixos, df_pontuais, df_rec_pontuais, df_caixinha, df_prog, df_status
    except Exception as e:
        st.warning("⚠️ Atualizando informações com a nuvem...")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

df_proj_all, df_fixos_all, df_pontuais_all, df_rec_pontuais_all, df_caixinha_all, df_prog_all, df_status_all = carregar_dados_globais()

def get_projecao(tipo, mes_tela):
    mes_banco = mes_tela_para_banco(mes_tela)
    if df_proj_all.empty:
        return pd.DataFrame(columns=['tipo', 'item', 'mes_ano', 'valor'])
    return df_proj_all[(df_proj_all['tipo'] == tipo) & (df_proj_all['mes_ano'] == mes_banco)]

def get_fixos_no_mes(mes_tela):
    mes_b = mes_tela_para_banco(mes_tela)
    if df_fixos_all.empty:
        return pd.DataFrame(columns=['item', 'valor'])
    
    df_p = df_fixos_all.copy()
    df_p['mes_ano'] = df_p['mes_ano'].fillna("09.2026").astype(str)
    
    df_mes = df_p[df_p['mes_ano'] == mes_b]
    if not df_mes.empty:
        return df_mes[['item', 'valor']]
    
    meses_anteriores = [m for m in df_p['mes_ano'].unique() if str(m) < mes_b]
    if meses_anteriores:
        ultimo_m = max(meses_anteriores)
        return df_p[df_p['mes_ano'] == ultimo_m][['item', 'valor']]
    
    return pd.DataFrame(columns=['item', 'valor'])

def get_programado_cartao():
    if df_prog_all.empty:
        return pd.DataFrame(columns=['id', 'cartao', 'descricao', 'valor'])
    return df_prog_all[['id', 'cartao', 'descricao', 'valor']]

def salvar_projecao_direta(tipo, item, mes_tela, valor):
    mes_b = mes_tela_para_banco(mes_tela)
    with engine.begin() as conn:
        query = '''
            INSERT INTO fam_projecao (tipo, item, mes_ano, valor)
            VALUES (:tipo, :item, :mes, :val)
            ON CONFLICT (tipo, item, mes_ano) 
            DO UPDATE SET valor = EXCLUDED.valor;
        '''
        conn.execute(text(query), {"tipo": tipo, "item": item, "mes": mes_b, "val": safe_float(valor)})
    salvar_ultimo_mes_banco(mes_tela)
    st.cache_data.clear()

def salvar_projecao(tipo, df_editado, meses_visiveis, mes_atual_foco):
    with engine.begin() as conn:
        for _, row in df_editado.iterrows():
            item = str(row['Item'])
            if "Total" in item:
                continue
            for mes_t in meses_visiveis:
                mes_b = mes_tela_para_banco(mes_t)
                val = safe_float(row[mes_t])
                query = '''
                    INSERT INTO fam_projecao (tipo, item, mes_ano, valor)
                    VALUES (:tipo, :item, :mes, :val)
                    ON CONFLICT (tipo, item, mes_ano) 
                    DO UPDATE SET valor = EXCLUDED.valor;
                '''
                conn.execute(text(query), {"tipo": tipo, "item": item, "mes": mes_b, "val": val})
    salvar_ultimo_mes_banco(mes_atual_foco)
    st.cache_data.clear()

def salvar_fixos_futuro(df_editado, mes_inicio_tela):
    idx_start = TODOS_MESES_TELA.index(mes_inicio_tela) if mes_inicio_tela in TODOS_MESES_TELA else 0
    meses_afetados_tela = TODOS_MESES_TELA[idx_start:]
    
    with engine.begin() as conn:
        for m_t in meses_afetados_tela:
            m_b = mes_tela_para_banco(m_t)
            conn.execute(text("DELETE FROM fam_gastos_fixos WHERE mes_ano = :mes"), {"mes": m_b})
            for _, row in df_editado.iterrows():
                item_str = str(row['item']).strip() if pd.notnull(row.get('item')) else ""
                if item_str:
                    val = safe_float(row['valor'])
                    query = text("INSERT INTO fam_gastos_fixos (item, mes_ano, valor) VALUES (:item, :mes, :val)")
                    conn.execute(query, {"item": item_str, "mes": m_b, "val": val})
                    
    salvar_ultimo_mes_banco(mes_inicio_tela)
    st.cache_data.clear()

def inser_gasto_rapido(mes_tela, descricao, categoria, valor):
    mes_b = mes_tela_para_banco(mes_tela)
    with engine.begin() as conn:
        query = '''
            INSERT INTO fam_pontuais_dinheiro (mes_ano, descricao, categoria, valor)
            VALUES (:mes_ano, :descricao, :categoria, :valor)
        '''
        conn.execute(text(query), {
            "mes_ano": mes_b, "descricao": descricao,
            "categoria": categoria, "valor": safe_float(valor)
        })
    salvar_ultimo_mes_banco(mes_tela)
    st.cache_data.clear()

def inser_receita_rapida(mes_tela, descricao, categoria, valor):
    mes_b = mes_tela_para_banco(mes_tela)
    with engine.begin() as conn:
        query = '''
            INSERT INTO fam_pontuais_receitas (mes_ano, descricao, categoria, valor)
            VALUES (:mes_ano, :descricao, :categoria, :valor)
        '''
        conn.execute(text(query), {
            "mes_ano": mes_b, "descricao": descricao,
            "categoria": categoria, "valor": safe_float(valor)
        })
    salvar_ultimo_mes_banco(mes_tela)
    st.cache_data.clear()

def deletar_gasto_pontual(gasto_id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fam_pontuais_dinheiro WHERE id = :id"), {"id": gasto_id})
    st.cache_data.clear()

def deletar_receita_pontual(rec_id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fam_pontuais_receitas WHERE id = :id"), {"id": rec_id})
    st.cache_data.clear()

def salvar_caixinha(df_editado, mes_atual_foco):
    with engine.begin() as conn:
        for _, row in df_editado.iterrows():
            mes_t = row['Mês']
            mes_b = mes_tela_para_banco(mes_t)
            val = safe_float(row['Aporte do Mês (R$)'])
            query = '''
                INSERT INTO fam_caixinha (mes_ano, valor)
                VALUES (:mes, :val)
                ON CONFLICT (mes_ano)
                DO UPDATE SET valor = EXCLUDED.valor;
            '''
            conn.execute(text(query), {"mes": mes_b, "val": val})
    salvar_ultimo_mes_banco(mes_atual_foco)
    st.cache_data.clear()

def salvar_programado_cartao(df_editado, mes_atual_foco):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fam_programado_cartao"))
        for _, row in df_editado.iterrows():
            if pd.notnull(row.get('descricao')) and str(row['descricao']).strip():
                cartao_val = str(row['cartao']) if pd.notnull(row.get('cartao')) else ESTRUTURA_CARTÕES_BASE[0]
                desc_val = str(row['descricao'])
                val_val = safe_float(row.get('valor'))
                query = "INSERT INTO fam_programado_cartao (cartao, descricao, valor) VALUES (:cartao, :desc, :val)"
                conn.execute(text(query), {"cartao": cartao_val, "desc": desc_val, "val": val_val})
    salvar_ultimo_mes_banco(mes_atual_foco)
    st.cache_data.clear()

# Cálculo Financeiro Familiar
def calcular_sequencia_financeira():
    prog_total = get_programado_cartao()['valor'].apply(safe_float).sum() if not df_prog_all.empty else 0.0

    dados_meses = {}
    saldo_acumulado_anterior = 0.0
    caixinha_acumulada_geral = 0.0

    meses_banco_seq = gerar_linha_tempo_tela("09.2026", 48)

    for m_b in meses_banco_seq:
        m_t = mes_banco_para_tela(m_b)

        df_fix = get_fixos_no_mes(m_t)
        fixos_val = df_fix['valor'].apply(safe_float).sum() if not df_fix.empty else 0.0

        renda_fixa = df_proj_all[(df_proj_all['mes_ano'] == m_b) & (df_proj_all['tipo'] == 'RECEITA') & (df_proj_all['item'].isin(ESTRUTURA_RECEITAS))]['valor'].apply(safe_float).sum() if not df_proj_all.empty else 0.0
        r_pontual_df = df_rec_pontuais_all[df_rec_pontuais_all['mes_ano'] == m_b] if not df_rec_pontuais_all.empty else pd.DataFrame()
        receita_pontual_mes = r_pontual_df['valor'].apply(safe_float).sum() if not r_pontual_df.empty else 0.0

        renda_mes_total = renda_fixa + receita_pontual_mes

        cartoes_mes = df_proj_all[(df_proj_all['mes_ano'] == m_b) & (df_proj_all['tipo'] == 'CARTAO') & (df_proj_all['item'].isin(ESTRUTURA_CARTÕES_BASE))]['valor'].apply(safe_float).sum() if not df_proj_all.empty else 0.0

        f_fechada = False
        if not df_status_all.empty:
            st_m = df_status_all[df_status_all['mes_ano'] == m_b]
            f_fechada = bool(st_m['fechada'].iloc[0]) if not st_m.empty else False

        add_prog = 0.0 if f_fechada else prog_total

        p_df = df_pontuais_all[df_pontuais_all['mes_ano'] == m_b] if not df_pontuais_all.empty else pd.DataFrame()
        gasto_pontual_mes = p_df['valor'].apply(safe_float).sum() if not p_df.empty else 0.0

        caixinha_mes = df_caixinha_all[df_caixinha_all['mes_ano'] == m_b]['valor'].apply(safe_float).sum() if not df_caixinha_all.empty else 0.0
        caixinha_acumulada_geral += caixinha_mes

        saidas_mes = (cartoes_mes + add_prog) + fixos_val + gasto_pontual_mes + caixinha_mes
        sobra_do_mes_bruta = renda_mes_total - saidas_mes
        
        saldo_herdeiro_abertura = saldo_acumulado_anterior
        
        saldo_disponivel_hoje = saldo_herdeiro_abertura + receita_pontual_mes - gasto_pontual_mes
        
        saldo_conta_final = saldo_acumulado_anterior + sobra_do_mes_bruta
        patrimonio_total_final = saldo_conta_final + caixinha_acumulada_geral

        dados_meses[m_t] = {
            "saldo_anterior": saldo_herdeiro_abertura,
            "saldo_disponivel_hoje": saldo_disponivel_hoje,
            "renda_mes": renda_mes_total,
            "saidas_mes": saidas_mes,
            "caixinha_mes": caixinha_mes,
            "caixinha_acumulada": caixinha_acumulada_geral,
            "sobra_mes_isolada": sobra_do_mes_bruta,
            "saldo_acumulado_final": saldo_conta_final,
            "patrimonio_total_final": patrimonio_total_final
        }
        saldo_acumulado_anterior = saldo_conta_final

    return dados_meses

dados_financeiros = calcular_sequencia_financeira()

# MENU LATERAL (SIDEBAR)
with st.sidebar:
    st.markdown("<h3 style='color:#60a5fa;'>⚡ Navegação Familiar</h3>", unsafe_allow_html=True)

    modo_visao = st.radio("Selecione a Visão:", ["⚡ Lançamento Rápido", "📈 Projeção Estratégica"], index=0)

    st.divider()

    ultimo_mes_salvo = carregar_ultimo_mes_salvo("10.2026")
    idx_padrao = TODOS_MESES_TELA.index(ultimo_mes_salvo) if ultimo_mes_salvo in TODOS_MESES_TELA else 0

    mes_atual = st.selectbox("📅 Mês Vigente:", TODOS_MESES_TELA[:36], index=idx_padrao)
    st.session_state["mes_atual_sel"] = mes_atual
    salvar_ultimo_mes_banco(mes_atual)

    if not modo_visao.startswith("⚡"):
        st.divider()
        modo_exibicao = st.radio("🔍 Período Visível:", ["6 Meses", "12 Meses"], index=0, horizontal=True)
    else:
        modo_exibicao = "6 Meses"

    st.divider()
    if st.button("🚪 Encerrar Sessão", use_container_width=True):
        st.session_state["autenticado_fam"] = False
        st.rerun()

idx_foco = TODOS_MESES_TELA.index(mes_atual)
qtd_meses = 6 if modo_exibicao == "6 Meses" else 12
meses_visiveis = TODOS_MESES_TELA[idx_foco:idx_foco + qtd_meses]
st.session_state["meses_v"] = meses_visiveis

d_foco = dados_financeiros.get(mes_atual, {
    "saldo_anterior": 0.0, "saldo_disponivel_hoje": 0.0, "renda_mes": 0.0,
    "saidas_mes": 0.0, "caixinha_mes": 0.0, "caixinha_acumulada": 0.0,
    "sobra_mes_isolada": 0.0, "saldo_acumulado_final": 0.0, "patrimonio_total_final": 0.0
})

# Cabeçalho Principal Familiar
st.markdown(f"""
    <div class="hero-banner-fam">
        <div>
            <div class="hero-title-fam">🏠 Painel Financeiro Familiar</div>
            <div style="color: #bfdbfe; font-size: 0.78rem; font-weight: 500; margin-top: 2px;">
                Mês de Referência Ativo: <b>{mes_atual}</b>
            </div>
        </div>
        <div class="hero-badge-fam">Orçamento Familiar</div>
    </div>
""", unsafe_allow_html=True)

def renderizar_painel_indicadores():
    st.markdown('<div class="section-header-fam">🔵 Status da Conta Corrente da Família</div>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="grid-sec1">
            <div class="card-base-fam card-saldo-ini">
                <span class="card-title-fam">🏦 Saldo Abertura Mês</span>
                <span class="card-val-fam">R$ {d_foco['saldo_anterior']:,.2f}</span>
            </div>
            <div class="card-base-fam card-disp">
                <span class="card-title-fam">💳 Disponível em Conta Hoje</span>
                <span class="card-val-fam" style="color:#38bdf8;">R$ {d_foco['saldo_disponivel_hoje']:,.2f}</span>
            </div>
            <div class="card-base-fam card-previsto">
                <span class="card-title-fam" style="color:#bfdbfe;">🏁 Saldo Projetado Fim do Mês</span>
                <span class="card-val-fam" style="color:#ffffff;">R$ {d_foco['saldo_acumulado_final']:,.2f}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header-fam">📊 Fluxo Mensal Familiar</div>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="grid-sec2">
            <div class="card-base-fam card-receita">
                <span class="card-title-fam">💵 Renda Familiar Total</span>
                <span class="card-val-fam" style="color:#34d399;">+ R$ {d_foco['renda_mes']:,.2f}</span>
            </div>
            <div class="card-base-fam card-despesa">
                <span class="card-title-fam">💸 Saídas e Compromissos</span>
                <span class="card-val-fam" style="color:#f43f5e;">- R$ {d_foco['saidas_mes']:,.2f}</span>
            </div>
            <div class="card-base-fam card-sobra">
                <span class="card-title-fam">⚖️ Sobra Isolada</span>
                <span class="card-val-fam" style="color:#f59e0b;">R$ {d_foco['sobra_mes_isolada']:,.2f}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-header-fam">🔒 Reservas & Patrimônio Familiar</div>', unsafe_allow_html=True)
    st.markdown(f"""
        <div class="grid-sec2">
            <div class="card-base-fam card-reserva">
                <span class="card-title-fam" style="color:#38bdf8;">🔒 Caixinha da Família</span>
                <span class="card-val-fam" style="color:#38bdf8;">R$ {d_foco['caixinha_acumulada']:,.2f}</span>
            </div>
            <div class="card-base-fam card-patrimonio">
                <span class="card-title-fam" style="color:#a78bfa;">💎 Patrimônio Familiar Total</span>
                <span class="card-val-fam" style="color:#a78bfa;">R$ {d_foco['patrimonio_total_final']:,.2f}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# ====================================================================
# SEÇÃO 1: MODO RÁPIDO
# ====================================================================
if modo_visao.startswith("⚡"):
    renderizar_painel_indicadores()

    st.divider()

    st.markdown(f"### 💳 Cartões da Família — **{mes_atual}**")
    
    with st.form(f"form_rapido_fam_{mes_atual}"):
        valores_cartoes = {}
        cols = st.columns(len(ESTRUTURA_CARTÕES_BASE))
        for idx, cartao in enumerate(ESTRUTURA_CARTÕES_BASE):
            with cols[idx]:
                df_c = get_projecao("CARTAO", mes_atual)
                val_atual = safe_float(df_c[df_c['item'] == cartao]['valor'].iloc[0]) if not df_c[df_c['item'] == cartao].empty else 0.0
                valores_cartoes[cartao] = st.number_input(f"{cartao} (R$)", value=val_atual, min_value=0.0, step=10.0, format="%.2f", key=f"fast_fam_{mes_atual}_{cartao}")
        
        if st.form_submit_button(f"💾 Atualizar Cartões da Família ({mes_atual})", type="primary", use_container_width=True):
            for cartao, val in valores_cartoes.items():
                salvar_projecao_direta("CARTAO", cartao, mes_atual, val)
            st.success("Faturas da família salvas!")
            st.rerun()

    st.divider()

    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        with st.expander(f"🟢 **Registrar Receita Rápida da Família (PIX / Extra)**", expanded=False):
            with st.form(f"form_receita_rapida_fam_{mes_atual}", clear_on_submit=True):
                desc_r = st.text_input("Descrição da Receita", placeholder="ex: Reembolso, Venda de item familiar, Pix")
                val_r = st.number_input("Valor Recebido (R$)", min_value=0.01, step=10.0, format="%.2f")
                cat_r = st.selectbox("Origem / Categoria", ["Pix / Transferência", "Trabalho Extra", "Vendas", "Reembolso", "Outros"])
                    
                if st.form_submit_button("💵 Adicionar ao Saldo da Família", type="primary", use_container_width=True):
                    if not desc_r.strip():
                        st.error("Insira a descrição da receita.")
                    else:
                        inser_receita_rapida(mes_atual, desc_r, cat_r, val_r)
                        st.success("Receita familiar adicionada ao saldo!")
                        st.rerun()

    with col_exp2:
        with st.expander(f"🔴 **Registrar Gasto Rápido da Família (PIX / Dinheiro)**", expanded=False):
            with st.form(f"form_gasto_rapido_fam_{mes_atual}", clear_on_submit=True):
                desc_g = st.text_input("Descrição do Gasto", placeholder="ex: Supermercado, Farmácia, Casa")
                val_g = st.number_input("Valor Pago (R$)", min_value=0.01, step=5.0, format="%.2f")
                cat_g = st.selectbox("Categoria", ["Mercado / Feira", "Saúde / Farmácia", "Escola / Filhos", "Casa / Manutenção", "Lazer Família", "Outros"])
                    
                if st.form_submit_button("💸 Deduzir do Saldo da Família", type="primary", use_container_width=True):
                    if not desc_g.strip():
                        st.error("Insira a descrição do gasto.")
                    else:
                        inser_gasto_rapido(mes_atual, desc_g, cat_g, val_g)
                        st.success("Gasto deduzido do saldo familiar!")
                        st.rerun()

# ====================================================================
# SEÇÃO 2: PROJEÇÃO COMPLETA & LONGO PRAZO
# ====================================================================
else:
    renderizar_painel_indicadores()

    st.divider()

    tab_geral, tab_caixinha = st.tabs([
        "📊 Planejamento Familiar",
        "📦 Caixinha da Família"
    ])

    with tab_geral:
        with st.form("form_financas_fam"):
            st.subheader("💵 1. Receitas Familiar Previstas (Fixas)")
            rows_rec = []
            for item in ESTRUTURA_RECEITAS:
                row_dict = {"Item": item}
                for mes_t in meses_visiveis:
                    df_item = get_projecao("RECEITA", mes_t)
                    val = df_item[df_item['item'] == item]['valor']
                    row_dict[mes_t] = safe_float(val.iloc[0]) if not val.empty else 0.0
                rows_rec.append(row_dict)
            
            row_total_rec = {"Item": "➕ Total Receitas Familiares"}
            for mes_t in meses_visiveis:
                soma_rec = sum(safe_float(r.get(mes_t)) for r in rows_rec)
                row_total_rec[mes_t] = soma_rec
            rows_rec.append(row_total_rec)

            df_rec_grid = pd.DataFrame(rows_rec)
            conf_rec = {mes: st.column_config.NumberColumn(f"{mes}", format="R$ %.2f", min_value=0.0) for mes in meses_visiveis}
            conf_rec["Item"] = st.column_config.TextColumn("Descrição", disabled=True)

            df_rec_edit = st.data_editor(
                df_rec_grid, num_rows="fixed", use_container_width=True, key="editor_rec_fam", height=190,
                column_config=conf_rec
            )

            st.divider()

            st.subheader("💳 2. Cartões de Crédito da Família")
            rows_cart = []
            for item in ESTRUTURA_CARTÕES_BASE:
                row_dict = {"Item": item}
                for mes_t in meses_visiveis:
                    df_cart_db = get_projecao("CARTAO", mes_t)
                    val = df_cart_db[df_cart_db['item'] == item]['valor']
                    row_dict[mes_t] = safe_float(val.iloc[0]) if not val.empty else 0.0
                rows_cart.append(row_dict)
                
            row_total_cart = {"Item": "💳 Total Cartões Família"}
            for mes_t in meses_visiveis:
                soma_cart = sum(safe_float(c.get(mes_t)) for c in rows_cart)
                row_total_cart[mes_t] = soma_cart
            rows_cart.append(row_total_cart)

            df_cart_grid = pd.DataFrame(rows_cart)
            conf_cart = {mes: st.column_config.NumberColumn(f"{mes}", format="R$ %.2f", min_value=0.0) for mes in meses_visiveis}
            conf_cart["Item"] = st.column_config.TextColumn("Cartão", disabled=True)

            df_cart_edit = st.data_editor(
                df_cart_grid, num_rows="fixed", use_container_width=True, key="editor_cart_fam", height=200,
                column_config=conf_cart
            )

            st.divider()

            st.subheader("🔮 3. Compras Parceladas / Assinaturas da Casa")
            df_prog_cart = get_programado_cartao()
            df_prog_edit = st.data_editor(
                df_prog_cart, num_rows="dynamic", use_container_width=True, key="editor_prog_fam", height=150,
                column_config={
                    "cartao": st.column_config.SelectboxColumn("Cartão Alvo", options=ESTRUTURA_CARTÕES_BASE),
                    "descricao": st.column_config.TextColumn("Descrição (ex: Escola, Seguro, Streaming)"),
                    "valor": st.column_config.NumberColumn("Valor Recorrente (R$)", format="R$ %.2f", min_value=0.0)
                }
            )

            st.divider()

            st.subheader(f"📌 4. Gastos Fixos da Casa / Família ({mes_atual} em diante)")
            df_fixos_db = get_fixos_no_mes(mes_atual)
            df_fixos_edit = st.data_editor(
                df_fixos_db, num_rows="dynamic", use_container_width=True, key="editor_fix_fam", height=150,
                column_config={
                    "item": st.column_config.TextColumn("Descrição da Despesa Ficha"),
                    "valor": st.column_config.NumberColumn("Valor Mensal (R$)", format="R$ %.2f", min_value=0.0)
                }
            )

            st.write("")
            btn_salvar_fam = st.form_submit_button("💾 Salvar Planejamento Familiar", type="primary", use_container_width=True)

            if btn_salvar_fam:
                salvar_projecao("RECEITA", df_rec_edit, meses_visiveis, mes_atual)
                salvar_projecao("CARTAO", df_cart_edit, meses_visiveis, mes_atual)
                salvar_programado_cartao(df_prog_edit, mes_atual)
                salvar_fixos_futuro(df_fixos_edit, mes_atual)
                st.success("Planejamento familiar atualizado!")
                st.rerun()

        st.divider()

        mes_b_atual = mes_tela_para_banco(mes_atual)
        
        c_ext1, c_ext2 = st.columns(2)

        with c_ext1:
            st.subheader("💵 Extrato de Receitas Rápidas Familiares")
            rec_pontuais_ind = df_rec_pontuais_all[df_rec_pontuais_all['mes_ano'] == mes_b_atual] if not df_rec_pontuais_all.empty else pd.DataFrame()
            if not rec_pontuais_ind.empty:
                for _, r in rec_pontuais_ind.iterrows():
                    c_r1, c_r2, c_r3, c_r4 = st.columns([4, 3, 3, 1])
                    c_r1.write(f"**{r['descricao']}**")
                    c_r2.write(f"🏷️ {r['categoria']}")
                    c_r3.write(f"**+ R$ {safe_float(r['valor']):,.2f}**")
                    if c_r4.button("🗑️", key=f"del_rec_fam_{r['id']}"):
                        deletar_receita_pontual(r['id'])
                        st.rerun()
            else:
                st.info("Nenhuma receita rápida registrada para a família neste mês.")

        with c_ext2:
            st.subheader("💸 Extrato de Gastos Esporádicos Familiares")
            pontuais_ind = df_pontuais_all[df_pontuais_all['mes_ano'] == mes_b_atual] if not df_pontuais_all.empty else pd.DataFrame()
            if not pontuais_ind.empty:
                for _, g in pontuais_ind.iterrows():
                    c_g1, c_g2, c_g3, c_g4 = st.columns([4, 3, 3, 1])
                    c_g1.write(f"**{g['descricao']}**")
                    c_g2.write(f"🏷️ {g['categoria']}")
                    c_g3.write(f"**- R$ {safe_float(g['valor']):,.2f}**")
                    if c_g4.button("🗑️", key=f"del_fam_{g['id']}"):
                        deletar_gasto_pontual(g['id'])
                        st.rerun()
            else:
                st.info("Nenhum gasto pontual familiar registrado no mês atual.")

    with tab_caixinha:
        st.header("📦 Reserva / Caixinha da Família")
        
        rows_caixinha = []
        acumulado_total_geral = 0.0
        acumulado_por_mes = {}
        
        for m_item in TODOS_MESES_TELA:
            val_db = df_caixinha_all[df_caixinha_all['mes_ano'] == mes_tela_para_banco(m_item)]['valor'] if not df_caixinha_all.empty else pd.Series()
            val_aporte = safe_float(val_db.iloc[0]) if not val_db.empty else 0.0
            acumulado_total_geral += val_aporte
            acumulado_por_mes[m_item] = acumulado_total_geral

        for mes_t in meses_visiveis:
            val = df_caixinha_all[df_caixinha_all['mes_ano'] == mes_tela_para_banco(mes_t)]['valor'] if not df_caixinha_all.empty else pd.Series()
            val_aporte = safe_float(val.iloc[0]) if not val.empty else 0.0
            total_ate_mes = acumulado_por_mes.get(mes_t, 0.0)
            
            rows_caixinha.append({
                "Mês": mes_t, 
                "Aporte do Mês (R$)": val_aporte,
                "Total Acumulado na Caixinha (R$)": total_ate_mes
            })
            
        df_caixinha_grid = pd.DataFrame(rows_caixinha)

        with st.form("form_caixinha_fam"):
            df_caixinha_edit = st.data_editor(
                df_caixinha_grid, num_rows="fixed", use_container_width=True, key="editor_caixinha_fam", height=180,
                column_config={
                    "Mês": st.column_config.TextColumn("Mês", disabled=True),
                    "Aporte do Mês (R$)": st.column_config.NumberColumn("Aporte do Mês (R$)", format="R$ %.2f", min_value=0.0),
                    "Total Acumulado na Caixinha (R$)": st.column_config.NumberColumn("Total Acumulado na Caixinha (R$)", format="R$ %.2f", disabled=True)
                }
            )
            btn_salvar_caixinha = st.form_submit_button("💾 Salvar Aportes da Caixinha", type="primary", use_container_width=True)
            if btn_salvar_caixinha:
                salvar_caixinha(df_caixinha_edit, mes_atual)
                st.success("Reserva familiar atualizada!")
                st.rerun()

        st.divider()

        st.subheader("📈 Visão Gráfica e Evolução da Saúde Financeira da Família")

        chart_data_list = []
        for m_t in meses_visiveis:
            d = dados_financeiros.get(m_t, {
                "saldo_anterior": 0.0, "saldo_disponivel_hoje": 0.0, "renda_mes": 0.0,
                "saidas_mes": 0.0, "caixinha_mes": 0.0, "caixinha_acumulada": 0.0,
                "sobra_mes_isolada": 0.0, "saldo_acumulado_final": 0.0, "patrimonio_total_final": 0.0
            })
            
            # Formatação ISO (AAAA-MM) para garantir a ordenação cronológica correta
            m_num, y_num = map(int, m_t.split("."))
            mes_iso = f"{y_num:04d}-{m_num:02d}"

            chart_data_list.append({
                "Mês": mes_iso,
                "Receitas": d["renda_mes"],
                "Despesas": d["saidas_mes"] - d["caixinha_mes"],
                "Sobra Líquida": d["sobra_mes_isolada"],
                "Saldo Previsto": d["saldo_acumulado_final"],
                "Patrimônio Total": d["patrimonio_total_final"]
            })

        df_chart = pd.DataFrame(chart_data_list)

        st.markdown("##### 💎 Trajetória do Patrimônio e Saldo da Família")
        st.line_chart(df_chart, x="Mês", y=["Patrimônio Total", "Saldo Previsto"], color=["#3b82f6", "#38bdf8"])

        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.markdown("##### ⚖️ Comparativo: Receitas vs. Despesas Familiares")
            st.bar_chart(df_chart, x="Mês", y=["Receitas", "Despesas"], color=["#34d399", "#f43f5e"], stack=False)

        with col_g2:
            st.markdown("##### 💵 Sobra Líquida Familiar Isolada por Mês")
            st.bar_chart(df_chart, x="Mês", y=["Sobra Líquida"], color=["#f59e0b"])

        with st.expander("🔍 **Ver Tabela Numérica Detalhada**", expanded=False):
            row_sal_ini = {"Métrica": "1. Saldo Inicial (Abertura Mês)"}
            row_sal_disp = {"Métrica": "2. Saldo Disponível Hoje (Em Conta)"}
            row_rec = {"Métrica": "3. Renda Total Familiar (Fixa + Extra)"}
            row_desp = {"Métrica": "4. Saídas Totais (Cartão + Fixos + PIX)"}
            row_caixinha = {"Métrica": "5. Aporte Caixinha (Mês)"}
            row_sobra_mes = {"Métrica": "6. Sobra Líquida Isolada do Mês"}
            row_sal_fim = {"Métrica": "7. Saldo Final Previsto (Fim Mês)"}
            row_reserva_acum = {"Métrica": "8. Caixinha Acumulada (Reserva)"}
            row_patrimonio = {"Métrica": "9. Patrimônio Total Geral"}

            for m_t in meses_visiveis:
                d = dados_financeiros.get(m_t, {
                    "saldo_anterior": 0.0, "saldo_disponivel_hoje": 0.0, "renda_mes": 0.0,
                    "saidas_mes": 0.0, "caixinha_mes": 0.0, "caixinha_acumulada": 0.0,
                    "sobra_mes_isolada": 0.0, "saldo_acumulado_final": 0.0, "patrimonio_total_final": 0.0
                })
                row_sal_ini[m_t] = d["saldo_anterior"]
                row_sal_disp[m_t] = d["saldo_disponivel_hoje"]
                row_rec[m_t] = d["renda_mes"]
                row_desp[m_t] = d["saidas_mes"] - d["caixinha_mes"]
                row_caixinha[m_t] = d["caixinha_mes"]
                row_sobra_mes[m_t] = d["sobra_mes_isolada"]
                row_sal_fim[m_t] = d["saldo_acumulado_final"]
                row_reserva_acum[m_t] = d["caixinha_acumulada"]
                row_patrimonio[m_t] = d["patrimonio_total_final"]

            df_resumo = pd.DataFrame([
                row_sal_ini, row_sal_disp, row_rec, row_desp, row_caixinha, row_sobra_mes, row_sal_fim, row_reserva_acum, row_patrimonio
            ])
            
            cols_conf = {mes: st.column_config.NumberColumn(format="R$ %.2f") for mes in meses_visiveis}
            st.dataframe(df_resumo, use_container_width=True, column_config=cols_conf, height=310)
