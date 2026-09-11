import os
from datetime import datetime
import streamlit as st
import pandas as pd
from sqlalchemy import create_engine, text

# 1. Configuração da Página
st.set_page_config(
    page_title="Gestão Financeira Familiar",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. Design System & CSS Avançado (Modo Escuro / Clean Moderno)
st.markdown("""
    <style>
        .stApp {
            background-color: #0b0f19;
            color: #f3f4f6;
        }
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 2rem !important;
            padding-left: 1.5rem !important;
            padding-right: 1.5rem !important;
        }
        
        /* Cartões de Métricas Executivos */
        .exec-card {
            background: linear-gradient(135deg, #111827 0%, #1f2937 100%);
            border: 1px solid #374151;
            border-radius: 12px;
            padding: 16px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            height: 100%;
        }
        .exec-card-title {
            font-size: 0.75rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #9ca3af;
            font-weight: 600;
            margin-bottom: 6px;
        }
        .exec-card-value {
            font-size: 1.25rem;
            font-weight: 700;
            color: #ffffff;
        }
        
        /* Tabelas e Editores */
        [data-testid="stDataFrame"] div, [data-testid="stDataEditor"] div {
            font-size: 0.82rem !important;
        }
        
        /* Abas Estilizadas */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background-color: #111827;
            padding: 6px;
            border-radius: 10px;
            border: 1px solid #374151;
        }
        .stTabs [data-baseweb="tab"] {
            height: 40px;
            border-radius: 6px;
            color: #9ca3af;
            font-weight: 600;
            font-size: 0.85rem;
        }
        .stTabs [aria-selected="true"] {
            background-color: #3b82f6 !important;
            color: white !important;
        }
        
        /* Botões customizados */
        .stButton > button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s ease;
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

    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("### 🔐 Controle Financeiro Familiar")
        st.markdown("Insira a senha de acesso para continuar.")
        with st.form("form_login"):
            senha_digitada = st.text_input("Senha:", type="password")
            botao_entrar = st.form_submit_button("Entrar no Sistema", use_container_width=True)
            if botao_entrar:
                if senha_digitada == "pretabebe":
                    st.session_state["autenticado"] = True
                    st.rerun()
                else:
                    st.error("Senha incorreta!")
    return False

if not verificar_senha():
    st.stop()

# 4. Conexão com o Banco de Dados (Supabase / Postgres)
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
        pool_size=2,
        max_overflow=3,
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
                    id SERIAL PRIMARY KEY, pessoa TEXT, item TEXT, mes_ano TEXT, valor DOUBLE PRECISION DEFAULT 0
                );
            '''))
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS gastos_comuns (
                    id SERIAL PRIMARY KEY, item TEXT, mes_ano TEXT, valor DOUBLE PRECISION DEFAULT 0, pagador TEXT DEFAULT 'Dividido (50/50)'
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
                    id SERIAL PRIMARY KEY, pessoa TEXT, cartao TEXT, descricao TEXT, mes_ano TEXT, valor DOUBLE PRECISION DEFAULT 0
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
            
            conn.execute(text('ALTER TABLE gastos_fixos ADD COLUMN IF NOT EXISTS mes_ano TEXT;'))
            conn.execute(text('ALTER TABLE gastos_comuns ADD COLUMN IF NOT EXISTS mes_ano TEXT;'))
            conn.execute(text('ALTER TABLE programado_cartao ADD COLUMN IF NOT EXISTS mes_ano TEXT;'))
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

@st.cache_data(ttl=30, show_spinner=False)
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
    if 'mes_ano' not in df_fixos.columns:
        df_fixos['mes_ano'] = '08.2026'
    if 'mes_ano' not in df_comuns.columns:
        df_comuns['mes_ano'] = '08.2026'
    if 'mes_ano' not in df_prog.columns:
        df_prog['mes_ano'] = '08.2026'
        
    return df_proj, df_fixos, df_comuns, df_pontuais, df_caixinha, df_prog, df_status

df_proj_all, df_fixos_all, df_comuns_all, df_pontuais_all, df_caixinha_all, df_prog_all, df_status_all = carregar_dados_globais()

def get_projecao(pessoa, tipo, mes_tela):
    mes_banco = mes_tela_para_banco(mes_tela)
    if df_proj_all.empty:
        return pd.DataFrame(columns=['pessoa', 'tipo', 'item', 'mes_ano', 'valor'])
    return df_proj_all[(df_proj_all['pessoa'] == pessoa) & (df_proj_all['tipo'] == tipo) & (df_proj_all['mes_ano'] == mes_banco)]

def get_fixos_mes(pessoa, mes_banco):
    if df_fixos_all.empty or 'mes_ano' not in df_fixos_all.columns:
        return pd.DataFrame(columns=['id', 'item', 'valor'])
    df_p = df_fixos_all[df_fixos_all['pessoa'] == pessoa]
    if df_p.empty:
        return pd.DataFrame(columns=['id', 'item', 'valor'])
    df_mes = df_p[df_p['mes_ano'] == mes_banco]
    if not df_mes.empty:
        return df_mes[['id', 'item', 'valor']]
    return pd.DataFrame(columns=['id', 'item', 'valor'])

def get_comuns_mes(mes_banco):
    if df_comuns_all.empty or 'mes_ano' not in df_comuns_all.columns:
        return pd.DataFrame(columns=['id', 'item', 'valor', 'pagador'])
    df_mes = df_comuns_all[df_comuns_all['mes_ano'] == mes_banco]
    if not df_mes.empty:
        return df_mes[['id', 'item', 'valor', 'pagador']]
    return pd.DataFrame(columns=['id', 'item', 'valor', 'pagador'])

def get_programado_cartao_mes(pessoa, mes_banco):
    if df_prog_all.empty or 'mes_ano' not in df_prog_all.columns:
        return pd.DataFrame(columns=['id', 'cartao', 'descricao', 'valor'])
    df_p = df_prog_all[df_prog_all['pessoa'] == pessoa]
    if df_p.empty:
        return pd.DataFrame(columns=['id', 'cartao', 'descricao', 'valor'])
    df_mes = df_p[df_p['mes_ano'] == mes_banco]
    if not df_mes.empty:
        return df_mes[['id', 'cartao', 'descricao', 'valor']]
    return pd.DataFrame(columns=['id', 'cartao', 'descricao', 'valor'])

# Funções de Salvamento no Banco
def salvar_projecao_direta(pessoa, tipo, item, mes_tela, valor):
    mes_b = mes_tela_para_banco(mes_tela)
    with engine.begin() as conn:
        query = '''
            INSERT INTO projecao (pessoa, tipo, item, mes_ano, valor)
            VALUES (:pessoa, :tipo, :item, :mes, :val)
            ON CONFLICT (pessoa, tipo, item, mes_ano) 
            DO UPDATE SET valor = EXCLUDED.valor;
        '''
        conn.execute(text(query), {"pessoa": pessoa, "tipo": tipo, "item": item, "mes": mes_b, "val": safe_float(valor)})
    salvar_ultimo_mes_banco(mes_tela)
    st.cache_data.clear()

def salvar_projecao_tabela(pessoa, tipo, df_editado, meses_visiveis, mes_atual_foco):
    with engine.begin() as conn:
        for _, row in df_editado.iterrows():
            item = str(row['Item'])
            if "Total" in item:
                continue
            for mes_t in meses_visiveis:
                mes_b = mes_tela_para_banco(mes_t)
                val = safe_float(row[mes_t])
                query = '''
                    INSERT INTO projecao (pessoa, tipo, item, mes_ano, valor)
                    VALUES (:pessoa, :tipo, :item, :mes, :val)
                    ON CONFLICT (pessoa, tipo, item, mes_ano) 
                    DO UPDATE SET valor = EXCLUDED.valor;
                '''
                conn.execute(text(query), {"pessoa": pessoa, "tipo": tipo, "item": item, "mes": mes_b, "val": val})
    salvar_ultimo_mes_banco(mes_atual_foco)
    st.cache_data.clear()

def salvar_fixos(pessoa, df_editado, mes_tela):
    mes_b = mes_tela_para_banco(mes_tela)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gastos_fixos WHERE pessoa = :pessoa AND mes_ano = :mes"), {"pessoa": pessoa, "mes": mes_b})
        for _, row in df_editado.iterrows():
            if pd.notnull(row.get('item')) and str(row['item']).strip():
                query = "INSERT INTO gastos_fixos (pessoa, item, mes_ano, valor) VALUES (:pessoa, :item, :mes, :val)"
                conn.execute(text(query), {"pessoa": pessoa, "item": str(row['item']), "mes": mes_b, "val": safe_float(row['valor'])})
    salvar_ultimo_mes_banco(mes_tela)
    st.cache_data.clear()

def salvar_comuns(df_editado, mes_tela):
    mes_b = mes_tela_para_banco(mes_tela)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gastos_comuns WHERE mes_ano = :mes"), {"mes": mes_b})
        for _, row in df_editado.iterrows():
            if pd.notnull(row.get('item')) and str(row['item']).strip():
                pag = str(row.get('pagador', 'Dividido (50/50)'))
                query = "INSERT INTO gastos_comuns (item, mes_ano, valor, pagador) VALUES (:item, :mes, :val, :pag)"
                conn.execute(text(query), {"item": str(row['item']), "mes": mes_b, "val": safe_float(row['valor']), "pag": pag})
    salvar_ultimo_mes_banco(mes_tela)
    st.cache_data.clear()

def salvar_programado_cartao(pessoa, df_editado, mes_tela):
    mes_b = mes_tela_para_banco(mes_tela)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM programado_cartao WHERE pessoa = :pessoa AND mes_ano = :mes"), {"pessoa": pessoa, "mes": mes_b})
        for _, row in df_editado.iterrows():
            if pd.notnull(row.get('descricao')) and str(row['descricao']).strip():
                cartao_val = str(row['cartao']) if pd.notnull(row.get('cartao')) else ESTRUTURA_CARTÕES_BASE[pessoa][0]
                desc_val = str(row['descricao'])
                val_val = safe_float(row.get('valor'))
                query = "INSERT INTO programado_cartao (pessoa, cartao, descricao, mes_ano, valor) VALUES (:pessoa, :cartao, :desc, :mes, :val)"
                conn.execute(text(query), {"pessoa": pessoa, "cartao": cartao_val, "desc": desc_val, "mes": mes_b, "val": val_val})
    salvar_ultimo_mes_banco(mes_tela)
    st.cache_data.clear()

def salvar_status_fatura(pessoa, mes_tela, fechada):
    mes_b = mes_tela_para_banco(mes_tela)
    with engine.begin() as conn:
        query = '''
            INSERT INTO status_faturas (pessoa, mes_ano, fechada)
            VALUES (:pessoa, :mes_ano, :fechada)
            ON CONFLICT (pessoa, mes_ano)
            DO UPDATE SET fechada = EXCLUDED.fechada;
        '''
        conn.execute(text(query), {"pessoa": pessoa, "mes_ano": mes_b, "fechada": fechada})
    salvar_ultimo_mes_banco(mes_tela)
    st.cache_data.clear()

def resetar_todos_status_faturas():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM status_faturas;"))
    st.cache_data.clear()

def inserir_gasto_rapido(mes_tela, pessoa, descricao, categoria, valor):
    mes_b = mes_tela_para_banco(mes_tela)
    with engine.begin() as conn:
        query = '''
            INSERT INTO pontuais_dinheiro (mes_ano, pessoa, descricao, categoria, valor)
            VALUES (:mes_ano, :pessoa, :descricao, :categoria, :valor)
        '''
        conn.execute(text(query), {
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
    with engine.begin() as conn:
        for _, row in df_editado.iterrows():
            mes_t = row['Mês']
            mes_b = mes_tela_para_banco(mes_t)
            val = safe_float(row['Aporte do Mês (R$)'])
            query = '''
                INSERT INTO caixinha (mes_ano, valor)
                VALUES (:mes, :val)
                ON CONFLICT (mes_ano)
                DO UPDATE SET valor = EXCLUDED.valor;
            '''
            conn.execute(text(query), {"mes": mes_b, "val": val})
    salvar_ultimo_mes_banco(mes_atual_foco)
    st.cache_data.clear()

# Motor de Cálculo Financeiro Integrado
def calcular_sequencia_financeira():
    dados_meses = {}
    saldo_acumulado_anterior = 0.0
    caixinha_acumulada_geral = 0.0
    meses_banco_seq = gerar_linha_tempo_tela("08.2026", 48)

    for m_b in meses_banco_seq:
        m_t = mes_banco_para_tela(m_b)

        df_fix_p1_mes = get_fixos_mes("Pessoa 1", m_b)
        df_fix_p2_mes = get_fixos_mes("Pessoa 2", m_b)
        df_prog_p1_mes = get_programado_cartao_mes("Pessoa 1", m_b)
        df_prog_p2_mes = get_programado_cartao_mes("Pessoa 2", m_b)
        df_comuns_mes = get_comuns_mes(m_b)

        prog_p1 = df_prog_p1_mes['valor'].apply(safe_float).sum() if not df_prog_p1_mes.empty else 0.0
        prog_p2 = df_prog_p2_mes['valor'].apply(safe_float).sum() if not df_prog_p2_mes.empty else 0.0
        
        fix_p1 = df_fix_p1_mes['valor'].apply(safe_float).sum() if not df_fix_p1_mes.empty else 0.0
        fix_p2 = df_fix_p2_mes['valor'].apply(safe_float).sum() if not df_fix_p2_mes.empty else 0.0
        
        comuns_val_total = df_comuns_mes['valor'].apply(safe_float).sum() if not df_comuns_mes.empty else 0.0
        comuns_p1 = df_comuns_mes[df_comuns_mes['pagador'] == 'Pessoa 1']['valor'].apply(safe_float).sum() if not df_comuns_mes.empty else 0.0
        comuns_p2 = df_comuns_mes[df_comuns_mes['pagador'] == 'Pessoa 2']['valor'].apply(safe_float).sum() if not df_comuns_mes.empty else 0.0
        comuns_div = df_comuns_mes[df_comuns_mes['pagador'] == 'Dividido (50/50)']['valor'].apply(safe_float).sum() if not df_comuns_mes.empty else 0.0
        
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
        
        saldo_conta_final = saldo_acumulado_anterior + sobra_do_mes_bruta
        patrimonio_total_final = saldo_conta_final + caixinha_acumulada_geral

        dados_meses[m_t] = {
            "saldo_anterior": saldo_acumulado_anterior, "renda_mes": renda_mes,
            "renda_p1": r_p1, "renda_p2": r_p2, "gasto_p1": gasto_exclusivo_p1,
            "gasto_p2": gasto_exclusivo_p2, "saidas_mes": saidas_mes,
            "caixinha_mes": caixinha_mes, "caixinha_acumulada": caixinha_acumulada_geral,
            "sobra_mes_isolada": sobra_do_mes_bruta, "saldo_acumulado_final": saldo_conta_final,
            "patrimonio_total_final": patrimonio_total_final
        }
        saldo_acumulado_anterior = saldo_conta_final

    return dados_meses

dados_financeiros = calcular_sequencia_financeira()

# 5. SIDEBAR EXECUTIVO & CONTROLES DE NAVEGAÇÃO
with st.sidebar:
    st.markdown("### ⚙️ Painel de Controle")
    
    if st.button("💾 SALVAR ALTERAÇÕES", type="primary", use_container_width=True):
        mes_foco_atual = st.session_state.get("mes_atual_sel", "09.2026")
        meses_v = st.session_state.get("meses_v", [mes_foco_atual])
        
        # Salvar dados globais e editores ativos em session_state
        for p_code in ["p1", "p2"]:
            p_nome = "Pessoa 1" if p_code == "p1" else "Pessoa 2"
            if f"rec_{p_code}" in st.session_state:
                salvar_projecao_tabela(p_nome, "RECEITA", st.session_state[f"rec_{p_code}"], meses_v, mes_foco_atual)
            if f"cart_{p_code}" in st.session_state:
                salvar_projecao_tabela(p_nome, "CARTAO", st.session_state[f"cart_{p_code}"], meses_v, mes_foco_atual)
            if f"fix_{p_code}_{mes_foco_atual}" in st.session_state:
                salvar_fixos(p_nome, st.session_state[f"fix_{p_code}_{mes_foco_atual}"], mes_foco_atual)
            if f"prog_{p_code}_{mes_foco_atual}" in st.session_state:
                salvar_programado_cartao(p_nome, st.session_state[f"prog_{p_code}_{mes_foco_atual}"], mes_foco_atual)

        if f"comuns_editor_{mes_foco_atual}" in st.session_state:
            salvar_comuns(st.session_state[f"comuns_editor_{mes_foco_atual}"], mes_foco_atual)
            
        if "caixinha_editor" in st.session_state:
            salvar_caixinha(st.session_state["caixinha_editor"], mes_foco_atual)
        
        salvar_ultimo_mes_banco(mes_foco_atual)
        st.success("Dados salvos com sucesso!")
        st.rerun()

    st.divider()

    modo_visao = st.radio("Modo de Operação:", ["📊 Dashboard Executivo (Mês)", "📈 Projeção & Orçamento Plurianual"], index=0)

    st.divider()

    ultimo_mes_salvo = carregar_ultimo_mes_salvo("09.2026")
    idx_padrao = TODOS_MESES_TELA.index(ultimo_mes_salvo) if ultimo_mes_salvo in TODOS_MESES_TELA else 0

    mes_atual = st.selectbox("📅 Competência em Foco:", TODOS_MESES_TELA[:36], index=idx_padrao)
    st.session_state["mes_atual_sel"] = mes_atual
    salvar_ultimo_mes_banco(mes_atual)

    if not modo_visao.startswith("📊"):
        st.divider()
        modo_exibicao = st.radio("🔍 Horizonte de Análise:", ["6 Meses", "12 Meses"], index=0, horizontal=True)
        st.write("")
        if st.button("🔄 Resetar Status Faturas", use_container_width=True):
            resetar_todos_status_faturas()
            st.success("Status redefinidos!")
            st.rerun()
    else:
        modo_exibicao = "6 Meses"

    st.divider()
    if st.button("🚪 Encerrar Sessão", use_container_width=True):
        st.session_state["autenticado"] = False
        st.rerun()

idx_foco = TODOS_MESES_TELA.index(mes_atual)
qtd_meses = 6 if modo_exibicao == "6 Meses" else 12
meses_visiveis = TODOS_MESES_TELA[idx_foco:idx_foco + qtd_meses]
st.session_state["meses_v"] = meses_visiveis

d_foco = dados_financeiros.get(mes_atual, {
    "saldo_anterior": 0.0, "renda_mes": 0.0, "renda_p1": 0.0, "renda_p2": 0.0,
    "gasto_p1": 0.0, "gasto_p2": 0.0, "saidas_mes": 0.0, "caixinha_mes": 0.0,
    "caixinha_acumulada": 0.0, "sobra_mes_isolada": 0.0, "saldo_acumulado_final": 0.0,
    "patrimonio_total_final": 0.0
})

# ====================================================================
# SEÇÃO PRINCIPAL: LAYOUT REORGANIZADO COM ABAS LÓGICO-FINANCEIRAS
# ====================================================================

# O topo exibe um Resumo Executivo Geral da competência selecionada
st.markdown(f"## 📌 Painel Financeiro Consolidado — **Competência {mes_atual}**")

c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(f"""
        <div class="exec-card">
            <div class="exec-card-title">Saldo Inicial Conta</div>
            <div class="exec-card-value">R$ {d_foco['saldo_anterior']:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown(f"""
        <div class="exec-card">
            <div class="exec-card-title">Renda Total Família</div>
            <div class="exec-card-value" style="color: #34d399;">R$ {d_foco['renda_mes']:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown(f"""
        <div class="exec-card">
            <div class="exec-card-title">Saídas Totais Mês</div>
            <div class="exec-card-value" style="color: #f87171;">R$ {d_foco['saidas_mes']:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)
with c4:
    st.markdown(f"""
        <div class="exec-card">
            <div class="exec-card-title">Saldo Corrente Conta</div>
            <div class="exec-card-value" style="color: #60a5fa;">R$ {d_foco['saldo_acumulado_final']:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)
with c5:
    st.markdown(f"""
        <div class="exec-card" style="border-color: #d97706;">
            <div class="exec-card-title" style="color: #fbbf24;">Patrimônio Total Geral</div>
            <div class="exec-card-value" style="color: #fbbf24;">R$ {d_foco['patrimonio_total_final']:,.2f}</div>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# Nova hierarquia de abas otimizada e limpa
tab_visao_geral, tab_p1, tab_p2, tab_comuns, tab_plurianual = st.tabs([
    "🏠 Visão Geral & Caixinha",
    "👤 Pessoa 1 (Lucas)",
    "👤 Pessoa 2 (Marcella)",
    "🏡 Despesas Comuns & Fixas da Casa",
    "📈 Projeção Plurianual"
])

# --------------------------------------------------------------------
# ABA 1: VISÃO GERAL & CAIXINHA
# --------------------------------------------------------------------
with tab_visao_geral:
    st.markdown(f"### 🎯 Indicadores Detalhados de {mes_atual}")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"""
            * **Renda P1 (Lucas):** R$ {d_foco['renda_p1']:,.2f}
            * **Gastos P1 (Lucas):** R$ {d_foco['gasto_p1']:,.2f}
            * **Sobra Líquida Isolada do Mês:** R$ {d_foco['sobra_mes_isolada']:,.2f}
        """)
    with col_b:
        st.markdown(f"""
            * **Renda P2 (Marcella):** R$ {d_foco['renda_p2']:,.2f}
            * **Gastos P2 (Marcella):** R$ {d_foco['gasto_p2']:,.2f}
            * **Caixinha Acumulada (Reserva):** R$ {d_foco['caixinha_acumulada']:,.2f}
        """)
    
    st.divider()
    st.markdown("### 📦 Gestão da Caixinha de Reserva da Família")
    
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
    df_caixinha_edit = st.data_editor(
        df_caixinha_grid, num_rows="fixed", use_container_width=True, key="caixinha_editor", height=220,
        column_config={
            "Mês": st.column_config.TextColumn("Mês", disabled=True),
            "Aporte do Mês (R$)": st.column_config.NumberColumn("Aporte do Mês (R$)", format="R$ %.2f", min_value=0.0),
            "Total Acumulado na Caixinha (R$)": st.column_config.NumberColumn("Total Acumulado na Caixinha (R$)", format="R$ %.2f", disabled=True)
        }
    )
    st.session_state["caixinha_df"] = df_caixinha_edit

# --------------------------------------------------------------------
# FUNÇÃO REUTILIZÁVEL PARA RENDERIZAR OS DADOS DE CADA PESSOA
# --------------------------------------------------------------------
def renderizar_bloco_pessoa(pessoa, p_code):
    st.markdown(f"### 💰 Receitas ({mes_atual})")
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
        df_rec_grid, num_rows="fixed", use_container_width=True, key=f"rec_{p_code}", height=180,
        column_config=conf_rec
    )
    st.session_state[f"rec_{p_code}"] = df_rec_edit

    st.divider()

    st.markdown("### 💳 Faturas de Cartão de Crédito")
    mes_b_atual = mes_tela_para_banco(mes_atual)
    st_match = df_status_all[(df_status_all['pessoa'] == pessoa) & (df_status_all['mes_ano'] == mes_b_atual)] if not df_status_all.empty else pd.DataFrame()
    is_closed_db = bool(st_match['fechada'].iloc[0]) if not st_match.empty else False
    
    key_chk = f"chk_fat_{p_code}_{mes_atual}"
    if key_chk not in st.session_state:
        st.session_state[key_chk] = is_closed_db

    chk_fechada = st.checkbox(f"✅ Fatura de {mes_atual} Fechada / Processada", key=key_chk)
    if chk_fechada != is_closed_db:
        salvar_status_fatura(pessoa, mes_atual, chk_fechada)
        st.rerun()

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
        df_cart_grid, num_rows="fixed", use_container_width=True, key=f"cart_{p_code}", height=200,
        column_config=conf_cart
    )
    st.session_state[f"cart_{p_code}"] = df_cart_edit

    st.divider()

    st.markdown(f"### 🔮 Lançamentos Programados no Cartão ({mes_atual})")
    df_prog_cart = get_programado_cartao_mes(pessoa, mes_b_atual)
    df_prog_edit = st.data_editor(
        df_prog_cart, num_rows="dynamic", use_container_width=True, key=f"prog_{p_code}_{mes_atual}", height=150,
        column_config={
            "cartao": st.column_config.SelectboxColumn("Cartão", options=lista_cartoes_final),
            "descricao": st.column_config.TextColumn("Descrição (ex: Seguro, Netflix)"),
            "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    st.session_state[f"prog_{p_code}_{mes_atual}"] = df_prog_edit

    st.divider()

    st.markdown(f"### 📌 Gastos Fixos Individuais ({mes_atual})")
    df_fixos_db = get_fixos_mes(pessoa, mes_b_atual)
    df_fixos_edit = st.data_editor(
        df_fixos_db, num_rows="dynamic", use_container_width=True, key=f"fix_{p_code}_{mes_atual}", height=150,
        column_config={
            "item": st.column_config.TextColumn("Descrição do Gasto Fixo"),
            "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", min_value=0.0)
        }
    )
    st.session_state[f"fix_{p_code}_{mes_atual}"] = df_fixos_edit

    st.divider()

    st.markdown("### 💸 Gastos Esporádicos em PIX / Dinheiro")
    pontuais_p = df_pontuais_all[(df_pontuais_all['pessoa'] == pessoa) & (df_pontuais_all['mes_ano'] == mes_b_atual)] if not df_pontuais_all.empty else pd.DataFrame()
    if not pontuais_p.empty:
        for _, g in pontuais_p.iterrows():
            c_g1, c_g2, c_g3, c_g4 = st.columns([4, 3, 3, 1])
            c_g1.write(f"**{g['descricao']}**")
            c_g2.write(f"🏷️ {g['categoria']}")
            c_g3.write(f"**R$ {safe_float(g['valor']):,.2f}**")
            if c_g4.button("🗑️", key=f"del_{g['id']}_{p_code}"):
                deletar_gasto_pontual(g['id'])
                st.rerun()
    else:
        st.info("Nenhum gasto em PIX/dinheiro registrado para este mês.")

# --------------------------------------------------------------------
# ABA 2: PESSOA 1
# --------------------------------------------------------------------
with tab_p1:
    renderizar_bloco_pessoa("Pessoa 1", "p1")

# --------------------------------------------------------------------
# ABA 3: PESSOA 2
# --------------------------------------------------------------------
with tab_p2:
    renderizar_bloco_pessoa("Pessoa 2", "p2")

# --------------------------------------------------------------------
# ABA 4: DESPESAS COMUNS & FIXAS DA CASA
# --------------------------------------------------------------------
with tab_comuns:
    st.markdown(f"### 🏡 Despesas Comuns do Casal / Casa ({mes_atual})")
    st.caption("Gerencie aluguel, condomínio, internet, supermercado e contas da residência.")
    
    mes_b_atual = mes_tela_para_banco(mes_atual)
    df_comuns_mes = get_comuns_mes(mes_b_atual)
    df_comuns_edit = st.data_editor(
        df_comuns_mes, num_rows="dynamic", use_container_width=True, key=f"comuns_editor_{mes_atual}", height=300,
        column_config={
            "item": st.column_config.TextColumn("Descrição da Despesa Comum"),
            "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f", min_value=0.0),
            "pagador": st.column_config.SelectboxColumn("Responsável pelo Pagamento", options=["Pessoa 1", "Pessoa 2", "Dividido (50/50)"])
        }
    )
    st.session_state[f"comuns_editor_{mes_atual}"] = df_comuns_edit
    
    st.divider()
    st.markdown("### ➕ Adicionar Gasto Rápido Comum ou Individual (PIX / Dinheiro)")
    with st.form(f"form_gasto_rapido_comum_{mes_atual}", clear_on_submit=True):
        c_f1, c_f2 = st.columns(2)
        with c_f1:
            desc = st.text_input("Descrição do Gasto", placeholder="ex: Feira, Farmácia, Conta Luz")
            val = st.number_input("Valor (R$)", min_value=0.01, step=5.0, format="%.2f")
        with c_f2:
            pessoa_gasto = st.selectbox("Quem Pagou?", ["Comum / Casa", "Pessoa 1", "Pessoa 2"])
            cat = st.selectbox("Categoria", ["Mercado / Feira", "Barbeiro / Estética", "Lazer / Restaurante", "Transporte", "Farmácia", "Outros"])
            
        if st.form_submit_button("💾 Registrar Gasto Rápido", type="primary", use_container_width=True):
            if not desc.strip():
                st.error("Preencha a descrição.")
            else:
                inserir_gasto_rapido(mes_atual, pessoa_gasto, desc, cat, val)
                st.success("Gasto registrado com sucesso!")
                st.rerun()

# --------------------------------------------------------------------
# ABA 5: PROJEÇÃO PLURIANUAL
# --------------------------------------------------------------------
with tab_plurianual:
    st.markdown("### 📈 Projeção Evolutiva Mês a Mês & Saldo de Caixa Acumulado")
    st.caption("Acompanhe o fluxo financeiro projetado para o horizonte selecionado.")
    
    row_sal_ini = {"Métrica": "1. Saldo Inicial em Conta"}
    row_rec = {"Métrica": "2. Renda Total Família"}
    row_desp = {"Métrica": "3. Saídas Totais (Cartão + Fixos + PIX)"}
    row_caixinha = {"Métrica": "4. Aporte Caixinha (Mês)"}
    row_sobra_mes = {"Métrica": "5. Sobra Líquida Isolada do Mês"}
    row_sal_fim = {"Métrica": "6. Saldo Final Conta (Corrente - Disponível)"}
    row_reserva_acum = {"Métrica": "7. Caixinha Acumulada (Reserva Separada)"}
    row_patrimonio = {"Métrica": "8. Patrimônio Total Geral (Conta + Caixinha)"}

    for m_t in meses_visiveis:
        d = dados_financeiros.get(m_t, {
            "saldo_anterior": 0.0, "renda_mes": 0.0, "saidas_mes": 0.0,
            "caixinha_mes": 0.0, "caixinha_acumulada": 0.0, "sobra_mes_isolada": 0.0, "saldo_acumulado_final": 0.0,
            "patrimonio_total_final": 0.0
        })
        row_sal_ini[m_t] = d["saldo_anterior"]
        row_rec[m_t] = d["renda_mes"]
        row_desp[m_t] = d["saidas_mes"] - d["caixinha_mes"]
        row_caixinha[m_t] = d["caixinha_mes"]
        row_sobra_mes[m_t] = d["sobra_mes_isolada"]
        row_sal_fim[m_t] = d["saldo_acumulado_final"]
        row_reserva_acum[m_t] = d["caixinha_acumulada"]
        row_patrimonio[m_t] = d["patrimonio_total_final"]

    df_resumo = pd.DataFrame([
        row_sal_ini, row_rec, row_desp, row_caixinha, row_sobra_mes, row_sal_fim, row_reserva_acum, row_patrimonio
    ])
    
    cols_conf = {mes: st.column_config.NumberColumn(format="R$ %.2f") for mes in meses_visiveis}
    st.dataframe(df_resumo, use_container_width=True, column_config=cols_conf, height=350)
