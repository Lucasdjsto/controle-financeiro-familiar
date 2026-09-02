import os
from datetime import datetime
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

        .metric-card-reserva {
            background-color: #0f2942;
            border: 1px solid #38bdf8;
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
            .metric-card, .metric-card-reserva, .metric-card-sub { flex: 1 1 calc(33.33% - 10px); }
        }
        @media (max-width: 640px) {
            .metric-card, .metric-card-reserva, .metric-card-sub { flex: 1 1 100%; }
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

# Funções de Conversão de Mês Visual para Banco (Deslocamento de +1 mês)
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

def get_projecao(pessoa, tipo, mes_tela):
    mes_banco = mes_tela_para_banco(mes_tela)
    if df_proj_all.empty:
        return pd.DataFrame(columns=['pessoa', 'tipo', 'item', 'mes_ano', 'valor'])
    return df_proj_all[(df_proj_all['pessoa'] == pessoa) & (df_proj_all['tipo'] == tipo) & (df_proj_all['mes_ano'] == mes_banco)]

def get_fixos(pessoa):
    if df_fixos_all.empty:
        return pd.DataFrame(columns=['id', 'item', 'valor'])
    return df_fixos_all[df_fixos_all['pessoa'] == pessoa][['id', 'item', 'valor']]

def get_programado_cartao(pessoa):
    if df_prog_all.empty:
        return pd.DataFrame(columns=['id', 'cartao', 'descricao', 'valor'])
    return df_prog_all[df_prog_all['pessoa'] == pessoa][['id', 'cartao', 'descricao', 'valor']]

# 8. Funções de Escrita
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
    st.cache_data.clear()

def salvar_projecao(pessoa, tipo, df_editado, meses_visiveis):
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
            "mes_ano": mes_b,
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

def salvar_programado_cartao(pessoa, df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM programado_cartao WHERE pessoa = :pessoa"), {"pessoa": pessoa})
        for _, row in df_editado.iterrows():
            if pd.notnull(row.get('descricao')) and str(row['descricao']).strip():
                cartao_val = str(row['cartao']) if pd.notnull(row.get('cartao')) else ESTRUTURA_CARTÕES_BASE[pessoa][0]
                desc_val = str(row['descricao'])
                val_val = safe_float(row.get('valor'))
                query = "INSERT INTO programado_cartao (pessoa, cartao, descricao, valor) VALUES (:pessoa, :cartao, :desc, :val)"
                conn.execute(text(query), {"pessoa": pessoa, "cartao": cartao_val, "desc": desc_val, "val": val_val})

# 9. LÓGICA DE CÁLCULO FINANCEIRO OTIMIZADA E RIGOROSA
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
    caixinha_acumulada_geral = 0.0

    meses_banco_seq = gerar_linha_tempo_tela("08.2026", 48)

    for m_b in meses_banco_seq:
        m_t = mes_banco_para_tela(m_b)

        r_p1 = df_proj_all[(df_proj_all['mes_ano'] == m_b) & (df_proj_all['pessoa'] == 'Pessoa 1') & (df_proj_all['tipo'] == 'RECEITA') & (df_proj_all['item'].isin(ESTRUTURA_RECEITAS))]['valor'].apply(safe_float).sum() if not df_proj_all.empty else 0.0
        r_p2 = df_proj_all[(df_proj_all['mes_ano'] == m_b) & (df_proj_all['pessoa'] == 'Pessoa 2') & (df_proj_all['tipo'] == 'RECEITA') & (df_proj_all['item'].isin(ESTRUTURA_RECEITAS))]['valor'].apply(safe_float).sum() if not df_proj_all.empty else 0.0
        renda_mes = r_p1 + r_p2

        cartoes_p1_validos = ESTRUTURA_CARTÕES_BASE["Pessoa 1"]
        cartoes_p2_validos = ESTRUTURA_CARTÕES_BASE["Pessoa 2"]

        c_p1 = df_proj_all[(df_proj_all['mes_ano'] == m_b) & (df_proj_all['pessoa'] == 'Pessoa 1') & (df_proj_all['tipo'] == 'CARTAO') & (df_proj_all['item'].isin(cartoes_p1_validos))]['valor'].apply(safe_float).sum() if not df_proj_all.empty else 0.0
        c_p2 = df_proj_all[(df_proj_all['mes_ano'] == m_b) & (df_proj_all['pessoa'] == 'Pessoa 2') & (df_proj_all['tipo'] == 'CARTAO') & (df_proj_all['item'].isin(cartoes_p2_validos))]['valor'].apply(safe_float).sum() if not df_proj_all.empty else 0.0
        
        f1_fechada = False
        f2_fechada = False
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
            "saldo_anterior": saldo_acumulado_anterior,
            "renda_mes": renda_mes,
            "renda_p1": r_p1,
            "renda_p2": r_p2,
            "gasto_p1": gasto_exclusivo_p1,
            "gasto_p2": gasto_exclusivo_p2,
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

# 10. CABEÇALHO E CONTROLES
col_head, col_save_btn, col_logout_btn = st.columns([6, 3.5, 1.5])
with col_head:
    st.title("📊 Painel Financeiro Integrado")

with col_save_btn:
    st.write("")
    if st.button("💾 SALVAR PROJEÇÃO LONGO PRAZO", type="primary", use_container_width=True):
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

# SELECTOR DE MODO DE VISUALIZAÇÃO
modo_visao = st.radio(
    "Modo de Navegação:", 
    ["⚡ **Modo Rápido (Dia a Dia do Mês Atual)**", "📈 **Projeção Completa & Longo Prazo**"], 
    horizontal=True
)

st.divider()

# CONTROLES TEMPORAIS
idx_padrao = TODOS_MESES_TELA.index("09.2026") if "09.2026" in TODOS_MESES_TELA else 0

c_sel1, c_sel2, c_reset = st.columns([5, 4, 3])
with c_sel1:
    mes_atual = st.selectbox("📅 Mês de Referência:", TODOS_MESES_TELA[:36], index=idx_padrao)
    st.session_state["mes_atual_sel"] = mes_atual
with c_sel2:
    modo_exibicao = st.radio("🔍 Horizonte Futuro:", ["6 Meses", "12 Meses"], index=0, horizontal=True)
with c_reset:
    st.write("")
    if st.button("🔄 Resetar Status Faturas", help="Limpa do banco todos os status de Fatura Fechada acumulados"):
        resetar_todos_status_faturas()
        st.success("Status de faturas resetados no banco!")
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
# SEÇÃO 1: MODO RÁPIDO (EXCLUSIVO PARA O DIA A DIA DO MÊS CORRENTE)
# ====================================================================
if modo_visao.startswith("⚡"):
    st.markdown(f"### ⚡ Painel Diário Rápido — Referência: **{mes_atual}**")
    st.info("💡 **Dica:** Os valores exibidos abaixo correspondem exatamente ao mês selecionado acima. Ao alterar e salvar, eles atualizam de imediato o saldo em conta e a projeção de longo prazo.")

    # PAINEL DE RESUMO DO MÊS (5 CARDS)
    s_final = d_foco['saldo_acumulado_final']
    caixinha_acum = d_foco['caixinha_acumulada']
    patrimonio_final = d_foco['patrimonio_total_final']
    delta_class = "delta-positive" if patrimonio_final >= 0 else "delta-negative"
    delta_label = "↑ Positivo" if patrimonio_final >= 0 else "↓ Déficit"

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
            <div class="metric-card-reserva">
                <div class="metric-label" style="color:#38bdf8;">🔒 4. Caixinha Guardada (Reserva)</div>
                <div class="metric-value" style="color:#38bdf8;">R$ {caixinha_acum:,.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">5. Saldo Corrente em Conta</div>
                <div class="metric-value">R$ {s_final:,.2f}</div>
                <div class="{delta_class}">{delta_label} (Disponível)</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    # FORMULÁRIO DE ATUALIZAÇÃO RÁPIDA DE CARTÕES (Direcionado estritamente para 'mes_atual')
    col_rapido_p1, col_rapido_p2 = st.columns(2)

    with col_rapido_p1:
        st.subheader(f"💳 Atualização Rápida — Pessoa 1 (Lucas)")
        cartoes_p1 = ESTRUTURA_CARTÕES_BASE["Pessoa 1"]
        
        with st.form(f"form_rapido_p1_{mes_atual}"):
            st.markdown(f"**Faturas de Cartão ({mes_atual})**")
            valores_p1 = {}
            for cartao in cartoes_p1:
                df_c = get_projecao("Pessoa 1", "CARTAO", mes_atual)
                val_atual = safe_float(df_c[df_c['item'] == cartao]['valor'].iloc[0]) if not df_c[df_c['item'] == cartao].empty else 0.0
                valores_p1[cartao] = st.number_input(f"{cartao} (R$)", value=val_atual, min_value=0.0, step=10.0, format="%.2f", key=f"fast_p1_{mes_atual}_{cartao}")
            
            btn_save_p1 = st.form_submit_button(f"💾 Salvar Cartões P1 ({mes_atual})", type="primary", use_container_width=True)
            if btn_save_p1:
                for cartao, val in valores_p1.items():
                    salvar_projecao_direta("Pessoa 1", "CARTAO", cartao, mes_atual, val)
                st.cache_data.clear()
                st.success(f"Cartões da Pessoa 1 para {mes_atual} atualizados com sucesso!")
                st.rerun()

    with col_rapido_p2:
        st.subheader(f"💳 Atualização Rápida — Pessoa 2 (Marcella)")
        cartoes_p2 = ESTRUTURA_CARTÕES_BASE["Pessoa 2"]
        
        with st.form(f"form_rapido_p2_{mes_atual}"):
            st.markdown(f"**Faturas de Cartão ({mes_atual})**")
            valores_p2 = {}
            for cartao in cartoes_p2:
                df_c = get_projecao("Pessoa 2", "CARTAO", mes_atual)
                val_atual = safe_float(df_c[df_c['item'] == cartao]['valor'].iloc[0]) if not df_c[df_c['item'] == cartao].empty else 0.0
                valores_p2[cartao] = st.number_input(f"{cartao} (R$)", value=val_atual, min_value=0.0, step=10.0, format="%.2f", key=f"fast_p2_{mes_atual}_{cartao}")
            
            btn_save_p2 = st.form_submit_button(f"💾 Salvar Cartões P2 ({mes_atual})", type="primary", use_container_width=True)
            if btn_save_p2:
                for cartao, val in valores_p2.items():
                    salvar_projecao_direta("Pessoa 2", "CARTAO", cartao, mes_atual, val)
                st.cache_data.clear()
                st.success(f"Cartões da Pessoa 2 para {mes_atual} atualizados com sucesso!")
                st.rerun()

    st.divider()

    # REGISTRO RÁPIDO DE PIX / DINHEIRO
    with st.expander(f"➕ **Adicionar Gasto Rápido em {mes_atual} (PIX / Dinheiro)**", expanded=True):
        with st.form(f"form_gasto_rapido_fast_{mes_atual}", clear_on_submit=True):
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                desc = st.text_input("Descrição (ex: Feira, Farmácia, Uber)", placeholder="Digite a descrição...")
                val = st.number_input("Valor (R$)", min_value=0.01, step=5.0, format="%.2f")
            with c_f2:
                pessoa = st.selectbox("Quem Pagou?", ["Pessoa 1", "Pessoa 2", "Comum / Casa"])
                cat = st.selectbox("Categoria", ["Mercado / Feira", "Barbeiro / Estética", "Lazer / Restaurante", "Transporte", "Farmácia", "Outros"])
                
            btn_salvar_gasto = st.form_submit_button("💾 Registrar Gasto Esporádico", type="primary", use_container_width=True)
            
            if btn_salvar_gasto:
                if not desc.strip():
                    st.error("Por favor, preencha a descrição do gasto.")
                else:
                    inserir_gasto_rapido(mes_atual, pessoa, desc, cat, val)
                    st.success("Gasto registrado com sucesso!")
                    st.rerun()

# ====================================================================
# SEÇÃO 2: PROJEÇÃO COMPLETA & LONGO PRAZO
# ====================================================================
else:
    st.markdown(f"#### ⚡ Resumo Financeiro Consolidador - {mes_atual}")

    s_final = d_foco['saldo_acumulado_final']
    caixinha_acum = d_foco['caixinha_acumulada']
    patrimonio_final = d_foco['patrimonio_total_final']
    delta_class = "delta-positive" if patrimonio_final >= 0 else "delta-negative"
    delta_label = "↑ Positivo" if patrimonio_final >= 0 else "↓ Déficit"

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
            <div class="metric-card-reserva">
                <div class="metric-label" style="color:#38bdf8;">🔒 4. Caixinha Guardada (Reserva)</div>
                <div class="metric-value" style="color:#38bdf8;">R$ {caixinha_acum:,.2f}</div>
            </div>
            <div class="metric-card">
                <div class="metric-label">5. Saldo Corrente em Conta</div>
                <div class="metric-value">R$ {s_final:,.2f}</div>
                <div class="{delta_class}">{delta_label} (Disponível)</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    tab_p1, tab_p2, tab_comuns, tab_consolidado = st.tabs([
        "👤 Pessoa 1 (Lucas)", 
        "👤 Pessoa 2 (Marcella)", 
        "🏡 Despesas Comuns (Casa/Aluguel)",
        "🏠 Visão Consolidada & Caixinha"
    ])

    def renderizar_pessoa(pessoa, p_code):
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
            df_rec_grid, num_rows="fixed", use_container_width=True, key=f"rec_{p_code}", height=190,
            column_config=conf_rec
        )
        st.session_state[f"rec_{p_code}_df"] = df_rec_edit

        st.divider()

        st.subheader("💳 2. Evolução das Faturas de Cartão de Crédito")
        
        mes_b_atual = mes_tela_para_banco(mes_atual)
        st_match = df_status_all[(df_status_all['pessoa'] == pessoa) & (df_status_all['mes_ano'] == mes_b_atual)] if not df_status_all.empty else pd.DataFrame()
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
            df_cart_grid, num_rows="fixed", use_container_width=True, key=f"cart_{p_code}", height=220,
            column_config=conf_cart
        )
        st.session_state[f"cart_{p_code}_df"] = df_cart_edit

        st.divider()

        st.subheader("🔮 3. Lançamentos Programados no Cartão (Seguros / Assinaturas Futuras)")
        df_prog_cart = get_programado_cartao(pessoa)
        df_prog_edit = st.data_editor(
            df_prog_cart, num_rows="dynamic", use_container_width=True, key=f"prog_{p_code}", height=150,
            column_config={
                "cartao": st.column_config.SelectboxColumn("Cartão", options=lista_cartoes_final),
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
        st.dataframe(df_resumo, use_container_width=True, column_config=cols_conf, height=280)
