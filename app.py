import os
import io
from datetime import datetime
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# 1. Configuração da Página
st.set_page_config(
    page_title="Sistema Integrado de Gestão Financeira",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. CSS Otimizado com Suporte a Estilos Dinâmicos
st.markdown("""
    <style>
        .block-container {
            padding-top: 0.5rem !important;
            padding-bottom: 0.8rem !important;
            padding-left: 0.4rem !important;
            padding-right: 0.4rem !important;
        }
        
        [data-testid="stDataFrame"] div, [data-testid="stDataEditor"] div {
            font-size: 0.78rem !important;
        }
        
        .stDataFrame [data-testid="stTable"] td, .stDataFrame [data-testid="stTable"] th {
            padding: 2px 4px !important;
        }
        
        .exec-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 6px;
            width: 100%;
            margin-bottom: 0.6rem;
        }
        
        .exec-box {
            background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
            border: 1px solid #374151;
            border-radius: 8px;
            padding: 8px 10px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        
        .exec-box-disponivel { background: #064e3b; border: 1px solid #059669; }
        .exec-box-reserva { background: #0c2340; border: 1px solid #0284c7; }
        .exec-box-final { background: #1e1b4b; border: 1px solid #6366f1; }
        .exec-box-patrimonio { background: #422006; border: 1px solid #d97706; grid-column: span 2; }
        .exec-box-alerta { background: #450a0a !important; border: 1px solid #ef4444 !important; }
        
        .exec-title { font-size: 0.65rem; color: #9ca3af; font-weight: 500; margin-bottom: 2px; }
        .exec-val { font-size: 0.88rem; font-weight: 700; color: #f3f4f6; }

        .stTabs [data-baseweb="tab-list"] {
            gap: 4px;
            background-color: #111827;
            padding: 4px;
            border-radius: 8px;
            border: 1px solid #374151;
        }
        
        .stTabs [data-baseweb="tab"] {
            height: 36px;
            border-radius: 6px;
            color: #9ca3af;
            font-weight: 600;
            font-size: 0.8rem;
        }
        
        .stTabs [aria-selected="true"] {
            background-color: #2563eb !important;
            color: white !important;
        }

        .stButton > button {
            border-radius: 5px;
            font-weight: 600;
            padding: 3px 8px;
            font-size: 0.78rem;
        }

        @media (min-width: 768px) {
            .exec-grid { grid-template-columns: repeat(3, 1fr); }
            .exec-box-patrimonio { grid-column: span 3; }
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

# 3. Autenticação por Senha
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
                st.error("Senha incorreta!")
    return False

if not verificar_senha():
    st.stop()

# 4. Conexão Otimizada com Supabase (PgBouncer/Connection Pool Ready)
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
        max_overflow=5,
        pool_recycle=60,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5}
    )

engine = get_db_engine()

def init_db():
    try:
        with engine.begin() as conn:
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS projecao (
                    pessoa TEXT, tipo TEXT, item TEXT, mes_ano TEXT,
                    valor DOUBLE PRECISION DEFAULT 0,
                    PRIMARY KEY (pessoa, tipo, item, mes_ano)
                );
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS gastos_fixos (
                    pessoa TEXT, item TEXT, mes_ano TEXT,
                    valor DOUBLE PRECISION DEFAULT 0,
                    PRIMARY KEY (pessoa, item, mes_ano)
                );
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS gastos_comuns (
                    item TEXT, mes_ano TEXT,
                    valor DOUBLE PRECISION DEFAULT 0,
                    pagador TEXT DEFAULT 'Dividido (50/50)',
                    PRIMARY KEY (item, mes_ano)
                );
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS pontuais_dinheiro (
                    id SERIAL PRIMARY KEY, mes_ano TEXT, pessoa TEXT, descricao TEXT, categoria TEXT, valor DOUBLE PRECISION DEFAULT 0
                );
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS caixinha (
                    mes_ano TEXT PRIMARY KEY, valor DOUBLE PRECISION DEFAULT 0
                );
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS programado_cartao (
                    id SERIAL PRIMARY KEY, pessoa TEXT, cartao TEXT, descricao TEXT, valor DOUBLE PRECISION DEFAULT 0
                );
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS status_faturas (
                    pessoa TEXT, mes_ano TEXT, fechada BOOLEAN DEFAULT FALSE,
                    PRIMARY KEY (pessoa, mes_ano)
                );
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS preferencias (
                    chave TEXT PRIMARY KEY, valor TEXT
                );
            '''))
    except Exception as e:
        st.error(f"Erro de Conexão com o Banco de Dados: {e}")

init_db()

def carregar_ultimo_mes_salvo(default="09.2026"):
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT valor FROM preferencias WHERE chave = 'ultimo_mes'")).fetchone()
            if res and res[0]:
                return res[0]
    except:
        pass
    return default

def salvar_ultimo_mes_banco(mes_tela):
    try:
        with engine.begin() as conn:
            conn.execute(text('''
                INSERT INTO preferencias (chave, valor) VALUES ('ultimo_mes', :mes)
                ON CONFLICT (chave) DO UPDATE SET valor = EXCLUDED.valor;
            '''), {"mes": mes_tela})
    except:
        pass

def gerar_linha_tempo_tela(mes_inicio_str="09.2026", quantidade_meses=48):
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

TODOS_MESES_TELA = gerar_linha_tempo_tela("09.2026", 48)

ESTRUTURA_CARTÕES_BASE = {
    "Pessoa 1": ["C6 Carbon", "Nubank", "Santander"],
    "Pessoa 2": ["Banco do Brasil", "Rico", "C6", "Amazon"]
}

ESTRUTURA_RECEITAS = ["Salário Base", "Receita Extra", "Receita Extra 1", "Receita Extra 2"]

@st.cache_data(ttl=60, show_spinner=False)
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

def get_projecao(pessoa, tipo, mes_tela):
    mes_banco = mes_tela_para_banco(mes_tela)
    if df_proj_all.empty:
        return pd.DataFrame(columns=['pessoa', 'tipo', 'item', 'mes_ano', 'valor'])
    return df_proj_all[(df_proj_all['pessoa'] == pessoa) & (df_proj_all['tipo'] == tipo) & (df_proj_all['mes_ano'] == mes_banco)]

def get_fixos_no_mes(pessoa, mes_tela):
    mes_b = mes_tela_para_banco(mes_tela)
    if df_fixos_all.empty:
        return pd.DataFrame(columns=['item', 'valor'])
    
    df_p = df_fixos_all[df_fixos_all['pessoa'] == pessoa].copy()
    df_p['mes_ano'] = df_p['mes_ano'].fillna("08.2026").astype(str)
    
    df_mes = df_p[df_p['mes_ano'] == mes_b]
    if not df_mes.empty:
        return df_mes[['item', 'valor']]
    
    meses_anteriores = [m for m in df_p['mes_ano'].unique() if str(m) <= mes_b]
    if meses_anteriores:
        ultimo_m = max(meses_anteriores)
        return df_p[df_p['mes_ano'] == ultimo_m][['item', 'valor']]
    
    return df_p[['item', 'valor']]

def get_comuns_no_mes(mes_tela):
    mes_b = mes_tela_para_banco(mes_tela)
    if df_comuns_all.empty:
        return pd.DataFrame(columns=['item', 'valor', 'pagador'])
    
    df_c = df_comuns_all.copy()
    df_c['mes_ano'] = df_c['mes_ano'].fillna("08.2026").astype(str)
    
    df_mes = df_c[df_c['mes_ano'] == mes_b]
    if not df_mes.empty:
        return df_mes[['item', 'valor', 'pagador']]
    
    meses_anteriores = [m for m in df_c['mes_ano'].unique() if str(m) <= mes_b]
    if meses_anteriores:
        ultimo_m = max(meses_anteriores)
        return df_c[df_c['mes_ano'] == ultimo_m][['item', 'valor', 'pagador']]
        
    return df_c[['item', 'valor', 'pagador']]

def get_programado_cartao(pessoa):
    if df_prog_all.empty:
        return pd.DataFrame(columns=['id', 'cartao', 'descricao', 'valor'])
    return df_prog_all[df_prog_all['pessoa'] == pessoa][['id', 'cartao', 'descricao', 'valor']]

# 5. Escritas em Lote (Bulk Upsert de Alta Performance)
def salvar_projecao_direta(pessoa, tipo, item, mes_tela, valor):
    mes_b = mes_tela_para_banco(mes_tela)
    with engine.begin() as conn:
        query = text('''
            INSERT INTO projecao (pessoa, tipo, item, mes_ano, valor)
            VALUES (:pessoa, :tipo, :item, :mes, :val)
            ON CONFLICT (pessoa, tipo, item, mes_ano) 
            DO UPDATE SET valor = EXCLUDED.valor;
        ''')
        conn.execute(query, {"pessoa": pessoa, "tipo": tipo, "item": item, "mes": mes_b, "val": safe_float(valor)})
    salvar_ultimo_mes_banco(mes_tela)
    st.cache_data.clear()

def salvar_projecao(pessoa, tipo, df_editado, meses_visiveis, mes_atual_foco):
    payload = []
    for _, row in df_editado.iterrows():
        item = str(row['Item'])
        if "Total" in item:
            continue
        for mes_t in meses_visiveis:
            mes_b = mes_tela_para_banco(mes_t)
            val = safe_float(row[mes_t])
            payload.append({"pessoa": pessoa, "tipo": tipo, "item": item, "mes": mes_b, "val": val})
            
    if payload:
        with engine.begin() as conn:
            query = text('''
                INSERT INTO projecao (pessoa, tipo, item, mes_ano, valor)
                VALUES (:pessoa, :tipo, :item, :mes, :val)
                ON CONFLICT (pessoa, tipo, item, mes_ano) 
                DO UPDATE SET valor = EXCLUDED.valor;
            ''')
            conn.execute(query, payload)
            
    salvar_ultimo_mes_banco(mes_atual_foco)
    st.cache_data.clear()

def salvar_fixos_futuro(pessoa, df_editado, mes_inicio_tela):
    idx_start = TODOS_MESES_TELA.index(mes_inicio_tela) if mes_inicio_tela in TODOS_MESES_TELA else 0
    meses_afetados_tela = TODOS_MESES_TELA[idx_start:]
    
    payload = []
    with engine.begin() as conn:
        for m_t in meses_afetados_tela:
            m_b = mes_tela_para_banco(m_t)
            conn.execute(text("DELETE FROM gastos_fixos WHERE pessoa = :pessoa AND mes_ano = :mes"), {"pessoa": pessoa, "mes": m_b})
            for _, row in df_editado.iterrows():
                if str(row['item']).strip():
                    payload.append({"pessoa": pessoa, "item": str(row['item']), "mes": m_b, "val": safe_float(row['valor'])})
        
        if payload:
            query = text('''
                INSERT INTO gastos_fixos (pessoa, item, mes_ano, valor)
                VALUES (:pessoa, :item, :mes, :val)
                ON CONFLICT (pessoa, item, mes_ano)
                DO UPDATE SET valor = EXCLUDED.valor;
            ''')
            conn.execute(query, payload)
                    
    salvar_ultimo_mes_banco(mes_inicio_tela)
    st.cache_data.clear()

def salvar_comuns_futuro(df_editado, mes_inicio_tela):
    idx_start = TODOS_MESES_TELA.index(mes_inicio_tela) if mes_inicio_tela in TODOS_MESES_TELA else 0
    meses_afetados_tela = TODOS_MESES_TELA[idx_start:]
    
    payload = []
    with engine.begin() as conn:
        for m_t in meses_afetados_tela:
            m_b = mes_tela_para_banco(m_t)
            conn.execute(text("DELETE FROM gastos_comuns WHERE mes_ano = :mes"), {"mes": m_b})
            for _, row in df_editado.iterrows():
                if str(row['item']).strip():
                    pag = str(row.get('pagador', 'Dividido (50/50)'))
                    payload.append({"item": str(row['item']), "mes": m_b, "val": safe_float(row['valor']), "pag": pag})
        
        if payload:
            query = text('''
                INSERT INTO gastos_comuns (item, mes_ano, valor, pagador)
                VALUES (:item, :mes, :val, :pag)
                ON CONFLICT (item, mes_ano)
                DO UPDATE SET valor = EXCLUDED.valor, pagador = EXCLUDED.pagador;
            ''')
            conn.execute(query, payload)
                    
    salvar_ultimo_mes_banco(mes_inicio_tela)
    st.cache_data.clear()

def arquivar_mes_manual(mes_tela):
    mes_b = mes_tela_para_banco(mes_tela)
    with engine.begin() as conn:
        conn.execute(text('''
            INSERT INTO status_faturas (pessoa, mes_ano, fechada) VALUES ('Pessoa 1', :mes, TRUE)
            ON CONFLICT (pessoa, mes_ano) DO UPDATE SET fechada = TRUE;
        '''), {"mes": mes_b})
        conn.execute(text('''
            INSERT INTO status_faturas (pessoa, mes_ano, fechada) VALUES ('Pessoa 2', :mes, TRUE)
            ON CONFLICT (pessoa, mes_ano) DO UPDATE SET fechada = TRUE;
        '''), {"mes": mes_b})
    salvar_ultimo_mes_banco(mes_tela)
    st.cache_data.clear()

def reabrir_mes_manual(mes_tela):
    mes_b = mes_tela_para_banco(mes_tela)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM status_faturas WHERE mes_ano = :mes;"), {"mes": mes_b})
    salvar_ultimo_mes_banco(mes_tela)
    st.cache_data.clear()

def resetar_todos_status_faturas():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM status_faturas;"))
    st.cache_data.clear()

def inserir_gasto_rapido(mes_tela, pessoa, descricao, categoria, valor):
    mes_b = mes_tela_para_banco(mes_tela)
    with engine.begin() as conn:
        query = text('''
            INSERT INTO pontuais_dinheiro (mes_ano, pessoa, descricao, categoria, valor)
            VALUES (:mes_ano, :pessoa, :descricao, :categoria, :valor)
        ''')
        conn.execute(query, {
            "mes_ano": mes_b, "pessoa": pessoa, "descricao": descricao,
            "categoria": categoria, "valor": safe_float(valor)
        })
    salvar_ultimo_mes_banco(mes_tela)
    st.cache_data.clear()

def deletar_gasto_pontual(gasto_id):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM pontuais_dinheiro WHERE id = :id"), {"id": gasto_id})
    st.cache_data.clear()

def salvar_caixinha(df_editado, mes_atual_foco):
    payload = []
    for _, row in df_editado.iterrows():
        mes_t = row['Mês']
        mes_b = mes_tela_para_banco(mes_t)
        val = safe_float(row['Aporte do Mês (R$)'])
        payload.append({"mes": mes_b, "val": val})
        
    if payload:
        with engine.begin() as conn:
            query = text('''
                INSERT INTO caixinha (mes_ano, valor)
                VALUES (:mes, :val)
                ON CONFLICT (mes_ano)
                DO UPDATE SET valor = EXCLUDED.valor;
            ''')
            conn.execute(query, payload)
            
    salvar_ultimo_mes_banco(mes_atual_foco)
    st.cache_data.clear()

def salvar_programado_cartao(pessoa, df_editado, mes_atual_foco):
    payload = []
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM programado_cartao WHERE pessoa = :pessoa"), {"pessoa": pessoa})
        for _, row in df_editado.iterrows():
            if pd.notnull(row.get('descricao')) and str(row['descricao']).strip():
                cartao_val = str(row['cartao']) if pd.notnull(row.get('cartao')) else ESTRUTURA_CARTÕES_BASE[pessoa][0]
                desc_val = str(row['descricao'])
                val_val = safe_float(row.get('valor'))
                payload.append({"pessoa": pessoa, "cartao": cartao_val, "desc": desc_val, "val": val_val})
                
        if payload:
            query = text("INSERT INTO programado_cartao (pessoa, cartao, descricao, valor) VALUES (:pessoa, :cartao, :desc, :val)")
            conn.execute(query, payload)
            
    salvar_ultimo_mes_banco(mes_atual_foco)
    st.cache_data.clear()

# 6. Motor de Cálculo Financeiro (Com Saldo Duplo e Caixa Vivo)
def calcular_sequencia_financeira():
    prog_p1 = get_programado_cartao("Pessoa 1")['valor'].apply(safe_float).sum() if not df_prog_all.empty else 0.0
    prog_p2 = get_programado_cartao("Pessoa 2")['valor'].apply(safe_float).sum() if not df_prog_all.empty else 0.0

    dados_meses = {}
    saldo_acumulado_anterior = 0.0
    caixinha_acumulada_geral = 0.0

    meses_banco_seq = gerar_linha_tempo_tela("08.2026", 48)

    for m_b in meses_banco_seq:
        m_t = mes_banco_para_tela(m_b)

        df_fix_p1 = get_fixos_no_mes("Pessoa 1", m_t)
        df_fix_p2 = get_fixos_no_mes("Pessoa 2", m_t)
        df_comuns_m = get_comuns_no_mes(m_t)

        fix_p1 = df_fix_p1['valor'].apply(safe_float).sum() if not df_fix_p1.empty else 0.0
        fix_p2 = df_fix_p2['valor'].apply(safe_float).sum() if not df_fix_p2.empty else 0.0

        comuns_val_total = df_comuns_m['valor'].apply(safe_float).sum() if not df_comuns_m.empty else 0.0
        comuns_p1 = df_comuns_m[df_comuns_m['pagador'] == 'Pessoa 1']['valor'].apply(safe_float).sum() if not df_comuns_m.empty else 0.0
        comuns_p2 = df_comuns_m[df_comuns_m['pagador'] == 'Pessoa 2']['valor'].apply(safe_float).sum() if not df_comuns_m.empty else 0.0
        comuns_div = df_comuns_m[df_comuns_m['pagador'] == 'Dividido (50/50)']['valor'].apply(safe_float).sum() if not df_comuns_m.empty else 0.0

        tot_fixos = fix_p1 + fix_p2 + comuns_val_total

        r_p1 = df_proj_all[(df_proj_all['mes_ano'] == m_b) & (df_proj_all['pessoa'] == 'Pessoa 1') & (df_proj_all['tipo'] == 'RECEITA') & (df_proj_all['item'].isin(ESTRUTURA_RECEITAS))]['valor'].apply(safe_float).sum() if not df_proj_all.empty else 0.0
        r_p2 = df_proj_all[(df_proj_all['mes_ano'] == m_b) & (df_proj_all['pessoa'] == 'Pessoa 2') & (df_proj_all['tipo'] == 'RECEITA') & (df_proj_all['item'].isin(ESTRUTURA_RECEITAS))]['valor'].apply(safe_float).sum() if not df_proj_all.empty else 0.0
        renda_mes = r_p1 + r_p2

        cartoes_p1_validos = ESTRUTURA_CARTÕES_BASE["Pessoa 1"]
        cartoes_p2_validos = ESTRUTURA_CARTÕES_BASE["Pessoa 2"]

        c_p1 = df_proj_all[(df_proj_all['mes_ano'] == m_b) & (df_proj_all['pessoa'] == 'Pessoa 1') & (df_proj_all['tipo'] == 'CARTAO') & (df_proj_all['item'].isin(cartoes_p1_validos))]['valor'].apply(safe_float).sum() if not df_proj_all.empty else 0.0
        c_p2 = df_proj_all[(df_proj_all['mes_ano'] == m_b) & (df_proj_all['pessoa'] == 'Pessoa 2') & (df_proj_all['tipo'] == 'CARTAO') & (df_proj_all['item'].isin(cartoes_p2_validos))]['valor'].apply(safe_float).sum() if not df_proj_all.empty else 0.0
        
        f1_fechada, f2_fechada = False, False
        if not df_status_all.empty:
            st1 = df_status_all[(df_status_all['pessoa'] == 'Pessoa 1') & (df_status_all['mes_ano'] == m_b)]
            f1_fechada = bool(st1['fechada'].iloc[0]) if not st1.empty else False
            st2 = df_status_all[(df_status_all['pessoa'] == 'Pessoa 2') & (df_status_all['mes_ano'] == m_b)]
            f2_fechada = bool(st2['fechada'].iloc[0]) if not st2.empty else False

        add_prog_p1 = 0.0 if f1_fechada else prog_p1
        add_prog_p2 = 0.0 if f2_fechada else prog_p2

        p_df = df_pontuais_all[df_pontuais_all['mes_ano'] == m_b] if not df_pontuais_all.empty else pd.DataFrame()
        pont_p1 = p_df[p_df['pessoa'] == 'Pessoa 1']['valor'].apply(safe_float).sum() if not p_df.empty else 0.0
        pont_p2 = p_df[p_df['pessoa'] == 'Pessoa 2']['valor'].apply(safe_float).sum() if not p_df.empty else 0.0
        pont_comum = p_df[p_df['pessoa'] == 'Comum / Casa']['valor'].apply(safe_float).sum() if not p_df.empty else 0.0
        pontual_mes = pont_p1 + pont_p2 + pont_comum

        gasto_exclusivo_p1 = (c_p1 + add_prog_p1) + fix_p1 + pont_p1 + comuns_p1 + (comuns_div / 2)
        gasto_exclusivo_p2 = (c_p2 + add_prog_p2) + fix_p2 + pont_p2 + comuns_p2 + (comuns_div / 2)

        caixinha_mes = df_caixinha_all[df_caixinha_all['mes_ano'] == m_b]['valor'].apply(safe_float).sum() if not df_caixinha_all.empty else 0.0
        caixinha_acumulada_geral += caixinha_mes

        saidas_mes = (c_p1 + c_p2 + add_prog_p1 + add_prog_p2) + tot_fixos + pontual_mes + caixinha_mes
        sobra_do_mes_bruta = renda_mes - saidas_mes
        
        # Visão Dupla de Saldo
        saldo_herdeiro_abertura = saldo_acumulado_anterior
        saldo_disponivel_hoje = saldo_herdeiro_abertura - pontual_mes
        
        saldo_conta_final = saldo_acumulado_anterior + sobra_do_mes_bruta
        patrimonio_total_final = saldo_conta_final + caixinha_acumulada_geral

        dados_meses[m_t] = {
            "saldo_anterior": saldo_herdeiro_abertura,
            "saldo_disponivel_hoje": saldo_disponivel_hoje,
            "renda_mes": renda_mes, "renda_p1": r_p1, "renda_p2": r_p2,
            "gasto_p1": gasto_exclusivo_p1, "gasto_p2": gasto_exclusivo_p2,
            "saidas_mes": saidas_mes, "caixinha_mes": caixinha_mes,
            "caixinha_acumulada": caixinha_acumulada_geral,
            "sobra_mes_isolada": sobra_do_mes_bruta,
            "saldo_acumulado_final": saldo_conta_final,
            "patrimonio_total_final": patrimonio_total_final
        }
        saldo_acumulado_anterior = saldo_conta_final

    return dados_meses

dados_financeiros = calcular_sequencia_financeira()

# 7. MENU LATERAL (SIDEBAR)
with st.sidebar:
    st.markdown("### ⚙️ Menu de Controle")

    modo_visao = st.radio("Modo de Navegação:", ["⚡ Modo Rápido (Dia a Dia)", "📈 Projeção Longo Prazo"], index=0)

    st.divider()

    ultimo_mes_salvo = carregar_ultimo_mes_salvo("09.2026")
    idx_padrao = TODOS_MESES_TELA.index(ultimo_mes_salvo) if ultimo_mes_salvo in TODOS_MESES_TELA else 0

    mes_atual = st.selectbox("📅 Mês de Referência:", TODOS_MESES_TELA[:36], index=idx_padrao)
    st.session_state["mes_atual_sel"] = mes_atual
    salvar_ultimo_mes_banco(mes_atual)

    if not modo_visao.startswith("⚡"):
        st.divider()
        modo_exibicao = st.radio("🔍 Horizonte Futuro:", ["6 Meses", "12 Meses"], index=0, horizontal=True)
        st.write("")
        if st.button("🔄 Resetar Status Faturas", use_container_width=True):
            resetar_todos_status_faturas()
            st.success("Status resetados!")
            st.rerun()
    else:
        modo_exibicao = "6 Meses"

    st.divider()
    
    # Exportação de Dados para Backup/Relatório em CSV
    if st.download_button(
        label="📥 Exportar Projeções (CSV)",
        data=pd.DataFrame(dados_financeiros).T.to_csv(index_label="Mês").encode("utf-8"),
        file_name=f"relatorio_financeiro_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True
    ):
        st.info("Download do relatório iniciado!")

    st.divider()
    if st.button("🚪 Sair do Sistema", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()

idx_foco = TODOS_MESES_TELA.index(mes_atual)
qtd_meses = 6 if modo_exibicao == "6 Meses" else 12
meses_visiveis = TODOS_MESES_TELA[idx_foco:idx_foco + qtd_meses]
st.session_state["meses_v"] = meses_visiveis

d_foco = dados_financeiros.get(mes_atual, {
    "saldo_anterior": 0.0, "saldo_disponivel_hoje": 0.0, "renda_mes": 0.0, "renda_p1": 0.0, "renda_p2": 0.0,
    "gasto_p1": 0.0, "gasto_p2": 0.0, "saidas_mes": 0.0, "caixinha_mes": 0.0,
    "caixinha_acumulada": 0.0, "sobra_mes_isolada": 0.0, "saldo_acumulado_final": 0.0,
    "patrimonio_total_final": 0.0
})

# Lógica Dinâmica para Alerta Vermelho em Caso de Saldo Negativo
class_disp = "exec-box-alerta" if d_foco['saldo_disponivel_hoje'] < 0 else "exec-box-disponivel"
class_final = "exec-box-alerta" if d_foco['saldo_acumulado_final'] < 0 else "exec-box-final"

# ====================================================================
# SEÇÃO 1: MODO RÁPIDO (DIA A DIA)
# ====================================================================
if modo_visao.startswith("⚡"):
    st.markdown(f"### ⚡ Painel Diário Rápido — **{mes_atual}**")

    s_final = d_foco['saldo_acumulado_final']
    caixinha_acum = d_foco['caixinha_acumulada']
    patrimonio_final = d_foco['patrimonio_total_final']

    st.markdown(f"""
        <div class="exec-grid">
            <div class="exec-box">
                <span class="exec-title">1. Saldo Inicial (Abertura Mês)</span>
                <span class="exec-val">R$ {d_foco['saldo_anterior']:,.2f}</span>
            </div>
            <div class="exec-box {class_disp}">
                <span class="exec-title" style="color:#6ee7b7;">2. Saldo Disponível Hoje (Em Conta)</span>
                <span class="exec-val" style="color:#6ee7b7;">R$ {d_foco['saldo_disponivel_hoje']:,.2f}</span>
            </div>
            <div class="exec-box">
                <span class="exec-title">3. Renda Total Família</span>
                <span class="exec-val" style="color:#34d399;">R$ {d_foco['renda_mes']:,.2f}</span>
            </div>
            <div class="exec-box">
                <span class="exec-title">4. Saídas Totais (Geral)</span>
                <span class="exec-val" style="color:#f87171;">R$ {d_foco['saidas_mes']:,.2f}</span>
            </div>
            <div class="exec-box exec-box-reserva">
                <span class="exec-title" style="color:#38bdf8;">🔒 5. Caixinha Guardada</span>
                <span class="exec-val" style="color:#38bdf8;">R$ {caixinha_acum:,.2f}</span>
            </div>
            <div class="exec-box {class_final}">
                <span class="exec-title" style="color:#a5b4fc;">6. Saldo Corrente Previsto (Fim Mês)</span>
                <span class="exec-val" style="color:#a5b4fc;">R$ {s_final:,.2f}</span>
            </div>
            <div class="exec-box">
                <span class="exec-title">👤 P1 (Lucas) Renda</span>
                <span class="exec-val" style="color:#60a5fa;">R$ {d_foco['renda_p1']:,.2f}</span>
            </div>
            <div class="exec-box">
                <span class="exec-title">👤 P1 (Lucas) Gastos</span>
                <span class="exec-val" style="color:#f87171;">R$ {d_foco['gasto_p1']:,.2f}</span>
            </div>
            <div class="exec-box">
                <span class="exec-title">👤 P2 (Marcella) Renda</span>
                <span class="exec-val" style="color:#60a5fa;">R$ {d_foco['renda_p2']:,.2f}</span>
            </div>
            <div class="exec-box">
                <span class="exec-title">👤 P2 (Marcella) Gastos</span>
                <span class="exec-val" style="color:#f87171;">R$ {d_foco['gasto_p2']:,.2f}</span>
            </div>
            <div class="exec-box exec-box-patrimonio">
                <span class="exec-title" style="color:#fbbf24;">💰 Patrimônio Total Geral (Conta + Caixinha)</span>
                <span class="exec-val" style="color:#fbbf24;">R$ {patrimonio_final:,.2f}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    col_rapido_p1, col_rapido_p2 = st.columns(2)

    with col_rapido_p1:
        st.subheader(f"💳 Cartões — P1 (Lucas)")
        cartoes_p1 = ESTRUTURA_CARTÕES_BASE["Pessoa 1"]
        
        with st.form(f"form_rapido_p1_{mes_atual}"):
            valores_p1 = {}
            for cartao in cartoes_p1:
                df_c = get_projecao("Pessoa 1", "CARTAO", mes_atual)
                val_atual = safe_float(df_c[df_c['item'] == cartao]['valor'].iloc[0]) if not df_c[df_c['item'] == cartao].empty else 0.0
                valores_p1[cartao] = st.number_input(f"{cartao} (R$)", value=val_atual, min_value=0.0, step=10.0, format="%.2f", key=f"fast_p1_{mes_atual}_{cartao}")
            
            if st.form_submit_button(f"💾 Salvar P1 ({mes_atual})", type="primary", use_container_width=True):
                for cartao, val in valores_p1.items():
                    salvar_projecao_direta("Pessoa 1", "CARTAO", cartao, mes_atual, val)
                st.success("Salvo com sucesso!")
                st.rerun()

    with col_rapido_p2:
        st.subheader(f"💳 Cartões — P2 (Marcella)")
        cartoes_p2 = ESTRUTURA_CARTÕES_BASE["Pessoa 2"]
        
        with st.form(f"form_rapido_p2_{mes_atual}"):
            valores_p2 = {}
            for cartao in cartoes_p2:
                df_c = get_projecao("Pessoa 2", "CARTAO", mes_atual)
                val_atual = safe_float(df_c[df_c['item'] == cartao]['valor'].iloc[0]) if not df_c[df_c['item'] == cartao].empty else 0.0
                valores_p2[cartao] = st.number_input(f"{cartao} (R$)", value=val_atual, min_value=0.0, step=10.0, format="%.2f", key=f"fast_p2_{mes_atual}_{cartao}")
            
            if st.form_submit_button(f"💾 Salvar P2 ({mes_atual})", type="primary", use_container_width=True):
                for cartao, val in valores_p2.items():
                    salvar_projecao_direta("Pessoa 2", "CARTAO", cartao, mes_atual, val)
                st.success("Salvo com sucesso!")
                st.rerun()

    st.divider()

    with st.expander(f"➕ **Adicionar Gasto Rápido em {mes_atual} (PIX / Dinheiro)**", expanded=False):
        with st.form(f"form_gasto_rapido_fast_{mes_atual}", clear_on_submit=True):
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                desc = st.text_input("Descrição", placeholder="ex: Feira, Farmácia")
                val = st.number_input("Valor (R$)", min_value=0.01, step=5.0, format="%.2f")
            with c_f2:
                pessoa = st.selectbox("Quem Pagou?", ["Pessoa 1", "Pessoa 2", "Comum / Casa"])
                cat = st.selectbox("Categoria", ["Mercado / Feira", "Barbeiro / Estética", "Lazer / Restaurante", "Transporte", "Farmácia", "Outros"])
                
            if st.form_submit_button("💾 Registrar Gasto", type="primary", use_container_width=True):
                if not desc.strip():
                    st.error("Preencha a descrição.")
                else:
                    inserir_gasto_rapido(mes_atual, pessoa, desc, cat, val)
                    st.success("Registrado com sucesso!")
                    st.rerun()

# ====================================================================
# SEÇÃO 2: PROJEÇÃO COMPLETA & LONGO PRAZO
# ====================================================================
else:
    st.markdown(f"#### ⚡ Resumo Consolidador — **{mes_atual}**")

    s_final = d_foco['saldo_acumulado_final']
    caixinha_acum = d_foco['caixinha_acumulada']
    patrimonio_final = d_foco['patrimonio_total_final']

    st.markdown(f"""
        <div class="exec-grid">
            <div class="exec-box">
                <span class="exec-title">1. Saldo Inicial (Abertura Mês)</span>
                <span class="exec-val">R$ {d_foco['saldo_anterior']:,.2f}</span>
            </div>
            <div class="exec-box {class_disp}">
                <span class="exec-title" style="color:#6ee7b7;">2. Saldo Disponível Hoje (Em Conta)</span>
                <span class="exec-val" style="color:#6ee7b7;">R$ {d_foco['saldo_disponivel_hoje']:,.2f}</span>
            </div>
            <div class="exec-box">
                <span class="exec-title">3. Renda Total Família</span>
                <span class="exec-val" style="color:#34d399;">R$ {d_foco['renda_mes']:,.2f}</span>
            </div>
            <div class="exec-box">
                <span class="exec-title">4. Saídas Totais (Geral)</span>
                <span class="exec-val" style="color:#f87171;">R$ {d_foco['saidas_mes']:,.2f}</span>
            </div>
            <div class="exec-box exec-box-reserva">
                <span class="exec-title" style="color:#38bdf8;">🔒 5. Caixinha Guardada</span>
                <span class="exec-val" style="color:#38bdf8;">R$ {caixinha_acum:,.2f}</span>
            </div>
            <div class="exec-box {class_final}">
                <span class="exec-title" style="color:#a5b4fc;">6. Saldo Corrente Previsto (Fim Mês)</span>
                <span class="exec-val" style="color:#a5b4fc;">R$ {s_final:,.2f}</span>
            </div>
            <div class="exec-box">
                <span class="exec-title">👤 P1 (Lucas) Renda</span>
                <span class="exec-val" style="color:#60a5fa;">R$ {d_foco['renda_p1']:,.2f}</span>
            </div>
            <div class="exec-box">
                <span class="exec-title">👤 P1 (Lucas) Gastos</span>
                <span class="exec-val" style="color:#f87171;">R$ {d_foco['gasto_p1']:,.2f}</span>
            </div>
            <div class="exec-box">
                <span class="exec-title">👤 P2 (Marcella) Renda</span>
                <span class="exec-val" style="color:#60a5fa;">R$ {d_foco['renda_p2']:,.2f}</span>
            </div>
            <div class="exec-box">
                <span class="exec-title">👤 P2 (Marcella) Gastos</span>
                <span class="exec-val" style="color:#f87171;">R$ {d_foco['gasto_p2']:,.2f}</span>
            </div>
            <div class="exec-box exec-box-patrimonio">
                <span class="exec-title" style="color:#fbbf24;">💰 Patrimônio Total Geral (Conta + Caixinha)</span>
                <span class="exec-val" style="color:#fbbf24;">R$ {patrimonio_final:,.2f}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    tab_consolidado, tab_p1, tab_p2, tab_comuns = st.tabs([
        "🏠 Visão Consolidada & Caixinha",
        "👤 Pessoa 1 (Lucas)", 
        "👤 Pessoa 2 (Marcella)", 
        "🏡 Despesas Comuns (Casa/Aluguel)"
    ])

    def renderizar_pessoa(pessoa, p_code):
        with st.form(f"form_pessoa_{p_code}"):
            st.subheader("💵 1. Receitas (Salário e Rendimentos)")
            rows_rec = []
            for item in ESTRUTURA_RECEITAS:
                row_dict = {"Item": item}
                for mes_t in meses_visiveis:
                    df_item = get_projecao(pessoa, "RECEITA", mes_t)
                    val = df_item[df_item['item'] == item]['valor']
                    row_dict[mes_t] = safe_float(val.iloc[0]) if not val.empty else 0.0
                rows_rec.append(row_dict)
            
            row_total_rec = {"Item": "➕ Total Receitas do Mês"}
            for mes_t in meses_visiveis:
                soma_rec = sum(safe_float(r.get(mes_t)) for r in rows_rec)
                row_total_rec[mes_t] = soma_rec
            rows_rec.append(row_total_rec)

            df_rec_grid = pd.DataFrame(rows_rec)
            conf_rec = {mes: st.column_config.NumberColumn(f"{mes}", format="R$ %.2f", min_value=0.0) for mes in meses_visiveis}
            conf_rec["Item"] = st.column_config.TextColumn("Item / Descrição", disabled=True)

            df_rec_edit = st.data_editor(
                df_rec_grid, num_rows="fixed", use_container_width=True, key=f"editor_rec_{p_code}", height=190,
                column_config=conf_rec
            )

            st.divider()

            st.subheader("💳 2. Evolução das Faturas de Cartão de Crédito")
            lista_cartoes_final = ESTRUTURA_CARTÕES_BASE[pessoa]

            rows_cart = []
            for item in lista_cartoes_final:
                row_dict = {"Item": item}
                for mes_t in meses_visiveis:
                    df_cart_db = get_projecao(pessoa, "CARTAO", mes_t)
                    val = df_cart_db[df_cart_db['item'] == item]['valor']
                    row_dict[mes_t] = safe_float(val.iloc[0]) if not val.empty else 0.0
                rows_cart.append(row_dict)
                
            row_total_cart = {"Item": "💳 Total Cartões do Mês"}
            for mes_t in meses_visiveis:
                soma_cart = sum(safe_float(c.get(mes_t)) for c in rows_cart)
                row_total_cart[mes_t] = soma_cart
            rows_cart.append(row_total_cart)

            df_cart_grid = pd.DataFrame(rows_cart)
            conf_cart = {mes: st.column_config.NumberColumn(f"{mes}", format="R$ %.2f", min_value=0.0) for mes in meses_visiveis}
            conf_cart["Item"] = st.column_config.TextColumn("Cartão", disabled=True)

            df_cart_edit = st.data_editor(
                df_cart_grid, num_rows="fixed", use_container_width=True, key=f"editor_cart_{p_code}", height=220,
                column_config=conf_cart
            )

            st.divider()

            st.subheader("🔮 3. Lançamentos Programados no Cartão")
            df_prog_cart = get_programado_cartao(pessoa)
            df_prog_edit = st.data_editor(
                df_prog_cart, num_rows="dynamic", use_container_width=True, key=f"editor_prog_{p_code}", height=150,
                column_config={
                    "cartao": st.column_config.SelectboxColumn("Cartão", options=lista_cartoes_final),
                    "descricao": st.column_config.TextColumn("Descrição (ex: Seguro, Netflix)"),
                    "valor": st.column_config.NumberColumn("Valor Previsto (R$)", format="R$ %.2f", min_value=0.0)
                }
            )

            st.divider()

            st.subheader(f"📌 4. Gastos Fixos Individuais Recorrentes ({mes_atual} em diante)")
            df_fixos_db = get_fixos_no_mes(pessoa, mes_atual)
            df_fixos_edit = st.data_editor(
                df_fixos_db, num_rows="dynamic", use_container_width=True, key=f"editor_fix_{p_code}", height=150,
                column_config={
                    "item": st.column_config.TextColumn("Descrição do Gasto Fixo Individual"),
                    "valor": st.column_config.NumberColumn("Valor Mensal (R$)", format="R$ %.2f", min_value=0.0)
                }
            )

            st.write("")
            btn_salvar_p = st.form_submit_button(f"💾 Aplicar e Salvar Dados de {pessoa}", type="primary", use_container_width=True)

            if btn_salvar_p:
                salvar_projecao(pessoa, "RECEITA", df_rec_edit, meses_visiveis, mes_atual)
                salvar_projecao(pessoa, "CARTAO", df_cart_edit, meses_visiveis, mes_atual)
                salvar_programado_cartao(pessoa, df_prog_edit, mes_atual)
                salvar_fixos_futuro(pessoa, df_fixos_edit, mes_atual)
                st.success(f"Dados de {pessoa} salvos com sucesso!")
                st.rerun()

        st.divider()

        st.subheader("💸 Extrato de Gastos Esporádicos (PIX / Dinheiro)")
        mes_b_atual = mes_tela_para_banco(mes_atual)
        pontuais_p = df_pontuais_all[(df_pontuais_all['pessoa'] == pessoa) & (df_pontuais_all['mes_ano'] == mes_b_atual)] if not df_pontuais_all.empty else pd.DataFrame()
        
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

    with tab_consolidado:
        st.header("🏠 Visão Consolidada, Caixinha & Totais")
        
        st.subheader(f"🔒 Encerramento e Congelamento do Mês — **{mes_atual}**")
        mes_b_atual = mes_tela_para_banco(mes_atual)
        st_match = df_status_all[df_status_all['mes_ano'] == mes_b_atual] if not df_status_all.empty else pd.DataFrame()
        is_mes_fechado = bool(st_match['fechada'].iloc[0]) if (not st_match.empty and 'fechada' in st_match.columns) else False

        col_st1, col_st2 = st.columns([3, 1])
        with col_st1:
            if is_mes_fechado:
                st.warning("⚠️ **Mês Fechado e Arquivado:** Os dados deste mês estão congelados no histórico.")
            else:
                st.info("ℹ️ **Mês Aberto:** Você pode editar, simular e navegar livremente sem alterar o passado.")

        with col_st2:
            if not is_mes_fechado:
                if st.button(f"🔒 Fechar Mês {mes_atual}", type="primary", use_container_width=True):
                    arquivar_mes_manual(mes_atual)
                    st.success(f"Mês {mes_atual} arquivado e congelado com sucesso!")
                    st.rerun()
            else:
                if st.button(f"🔓 Reabrir Mês {mes_atual}", use_container_width=True):
                    reabrir_mes_manual(mes_atual)
                    st.success(f"Mês {mes_atual} reaberto para edição!")
                    st.rerun()

        st.divider()

        st.subheader("📦 Caixinha de Reserva da Família (Acumulativa)")
        
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

        with st.form("form_caixinha"):
            df_caixinha_edit = st.data_editor(
                df_caixinha_grid, num_rows="fixed", use_container_width=True, key="editor_caixinha", height=200,
                column_config={
                    "Mês": st.column_config.TextColumn("Mês", disabled=True),
                    "Aporte do Mês (R$)": st.column_config.NumberColumn("Aporte do Mês (R$)", format="R$ %.2f", min_value=0.0),
                    "Total Acumulado na Caixinha (R$)": st.column_config.NumberColumn("Total Acumulado na Caixinha (R$)", format="R$ %.2f", disabled=True)
                }
            )
            btn_salvar_caixinha = st.form_submit_button("💾 Salvar Aportes da Caixinha", type="primary", use_container_width=True)
            if btn_salvar_caixinha:
                salvar_caixinha(df_caixinha_edit, mes_atual)
                st.success("Caixinha atualizada!")
                st.rerun()

        st.divider()

        st.subheader("📅 Projeção Evolutiva Mês a Mês & Saldo de Caixa Acumulado")
        
        row_sal_ini = {"Métrica": "1. Saldo Inicial (Abertura Mês)"}
        row_sal_disp = {"Métrica": "2. Saldo Disponível Hoje (Em Conta)"}
        row_rec = {"Métrica": "3. Renda Total Família"}
        row_desp = {"Métrica": "4. Saídas Totais (Cartão + Fixos + PIX)"}
        row_caixinha = {"Métrica": "5. Aporte Caixinha (Mês)"}
        row_sobra_mes = {"Métrica": "6. Sobra Líquida Isolada do Mês"}
        row_sal_fim = {"Métrica": "7. Saldo Final Previsto (Fim Mês)"}
        row_reserva_acum = {"Métrica": "8. Caixinha Acumulada (Reserva)"}
        row_patrimonio = {"Métrica": "9. Patrimônio Total Geral"}

        dados_grafico = []

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
            
            dados_grafico.append({
                "Mês": m_t,
                "Patrimônio Total": d["patrimonio_total_final"],
                "Saldo Conta": d["saldo_acumulado_final"],
                "Caixinha": d["caixinha_acumulada"]
            })

        df_resumo = pd.DataFrame([
            row_sal_ini, row_sal_disp, row_rec, row_desp, row_caixinha, row_sobra_mes, row_sal_fim, row_reserva_acum, row_patrimonio
        ])
        
        cols_conf = {mes: st.column_config.NumberColumn(format="R$ %.2f") for mes in meses_visiveis}
        st.dataframe(df_resumo, use_container_width=True, column_config=cols_conf, height=310)

        st.divider()
        
        # Gráfico Sintético de Evolução do Patrimônio Familiar
        st.subheader("📈 Curva de Crescimento do Patrimônio Familiar")
        df_chart = pd.DataFrame(dados_grafico).set_index("Mês")
        st.line_chart(df_chart, use_container_width=True)

    with tab_p1:
        renderizar_pessoa("Pessoa 1", "p1")

    with tab_p2:
        renderizar_pessoa("Pessoa 2", "p2")

    with tab_comuns:
        st.header("🏡 Despesas Comuns do Casal / Casa")
        with st.form("form_comuns"):
            df_comuns_edit = st.data_editor(
                get_comuns_no_mes(mes_atual), num_rows="dynamic", use_container_width=True, key="editor_comuns", height=220,
                column_config={
                    "item": st.column_config.TextColumn("Descrição da Despesa Comum"),
                    "valor": st.column_config.NumberColumn("Valor Mensal (R$)", format="R$ %.2f", min_value=0.0),
                    "pagador": st.column_config.SelectboxColumn("Responsável pelo Pagamento", options=["Pessoa 1", "Pessoa 2", "Dividido (50/50)"])
                }
            )
            btn_salvar_comuns = st.form_submit_button("💾 Salvar Despesas Comuns (Mês e Futuro)", type="primary", use_container_width=True)
            if btn_salvar_comuns:
                salvar_comuns_futuro(df_comuns_edit, mes_atual)
                st.success("Despesas comuns atualizadas para o futuro com sucesso!")
                st.rerun()
