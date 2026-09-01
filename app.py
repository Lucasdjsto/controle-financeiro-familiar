import os
import io
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

# 1. Configuração da Página
st.set_page_config(page_title="Sistema Integrado de Gestão Financeira", layout="wide")

# 2. CSS para Otimização Mobile
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 1.5rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        @media (max-width: 640px) {
            h1 { font-size: 1.4rem !important; }
            h2 { font-size: 1.2rem !important; }
            h3 { font-size: 1.0rem !important; }
            [data-testid="stMetricValue"] { font-size: 1.1rem !important; }
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
    senha_correta = os.getenv("APP_PASSWORD", "123456")
    
    with st.form("form_login"):
        senha_digitada = st.text_input("Digite a senha de acesso:", type="password")
        if st.form_submit_button("Entrar"):
            if senha_digitada == senha_correta:
                st.session_state["autenticado"] = True
                st.success("Acesso liberado!")
                st.rerun()
            else:
                st.error("Senha incorreta!")
    return False

if not verificar_senha():
    st.stop()

# 4. Conexão com o Banco Supabase
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

# 5. Inicialização do Banco
def init_db():
    with engine.begin() as conn:
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS projecao (
                pessoa TEXT, tipo TEXT, item TEXT, mes_ano TEXT, valor DOUBLE PRECISION DEFAULT 0,
                PRIMARY KEY (pessoa, tipo, item, mes_ano)
            );
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS gastos_fixos (
                id SERIAL PRIMARY KEY, pessoa TEXT, item TEXT, valor DOUBLE PRECISION DEFAULT 0
            );
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS gastos_comuns (
                id SERIAL PRIMARY KEY, item TEXT, valor DOUBLE PRECISION DEFAULT 0, pagador TEXT DEFAULT 'Pessoa 1'
            );
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS pontuais_dinheiro (
                id SERIAL PRIMARY KEY, mes_ano TEXT, pessoa TEXT, descricao TEXT, categoria TEXT, 
                tipo_debito TEXT DEFAULT 'Diário (Mês Atual)', valor DOUBLE PRECISION DEFAULT 0
            );
        '''))
        conn.execute(text('''
            CREATE TABLE IF NOT EXISTS caixinha (
                mes_ano TEXT PRIMARY KEY, valor DOUBLE PRECISION DEFAULT 0
            );
        '''))

init_db()

# 6. Estruturas Dinâmicas (Até 2030)
def gerar_meses_projecao():
    meses = []
    for ano in range(2026, 2031):
        m_start = 8 if ano == 2026 else 1
        m_end = 12
        for mes in range(m_start, m_end + 1):
            meses.append(f"{mes:02d}.{ano}")
    return meses

MESES_PROJECAO = gerar_meses_projecao()

ESTRUTURA_CARTÕES = {
    "Pessoa 1": ["C6 Carbon", "Nubank", "Santander"],
    "Pessoa 2": ["Banco do Brasil", "Rico / C6", "Amazon"]
}

ESTRUTURA_RECEITAS = {
    "Pessoa 1": ["Salário Base", "Receita Extra"],
    "Pessoa 2": ["Salário Base", "Receita Extra"]
}

# 7. Persistência
def carregar_projecao(pessoa, tipo):
    return pd.read_sql(text("SELECT * FROM projecao WHERE pessoa = :pessoa AND tipo = :tipo"), engine, params={"pessoa": pessoa, "tipo": tipo})

def salvar_projecao(pessoa, tipo, df_editado):
    with engine.begin() as conn:
        for _, row in df_editado.iterrows():
            item = row['Item']
            for mes in MESES_PROJECAO:
                val = float(row[mes]) if pd.notnull(row[mes]) else 0.0
                query = '''
                    INSERT INTO projecao (pessoa, tipo, item, mes_ano, valor)
                    VALUES (:pessoa, :tipo, :item, :mes, :val)
                    ON CONFLICT (pessoa, tipo, item, mes_ano) DO UPDATE SET valor = EXCLUDED.valor;
                '''
                conn.execute(text(query), {"pessoa": pessoa, "tipo": tipo, "item": item, "mes": mes, "val": val})

def carregar_fixos(pessoa):
    return pd.read_sql(text("SELECT id, item, valor FROM gastos_fixos WHERE pessoa = :pessoa"), engine, params={"pessoa": pessoa})

def salvar_fixos(pessoa, df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gastos_fixos WHERE pessoa = :pessoa"), {"pessoa": pessoa})
        for _, row in df_editado.iterrows():
            if str(row['item']).strip():
                conn.execute(text("INSERT INTO gastos_fixos (pessoa, item, valor) VALUES (:pessoa, :item, :val)"),
                             {"pessoa": pessoa, "item": str(row['item']), "val": float(row['valor'])})

def carregar_comuns():
    return pd.read_sql(text("SELECT id, item, valor, pagador FROM gastos_comuns"), engine)

def salvar_comuns(df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gastos_comuns"))
        for _, row in df_editado.iterrows():
            if str(row['item']).strip():
                conn.execute(text("INSERT INTO gastos_comuns (item, valor, pagador) VALUES (:item, :val, :pag)"),
                             {"item": str(row['item']), "val": float(row['valor']), "pag": str(row['pagador'])})

def carregar_pontuais(mes_ano):
    return pd.read_sql(text("SELECT id, pessoa, descricao, categoria, tipo_debito, valor FROM pontuais_dinheiro WHERE mes_ano = :mes_ano"), engine, params={"mes_ano": mes_ano})

def salvar_pontuais(mes_ano, df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM pontuais_dinheiro WHERE mes_ano = :mes_ano"), {"mes_ano": mes_ano})
        for _, row in df_editado.iterrows():
            if str(row['descricao']).strip():
                conn.execute(text("INSERT INTO pontuais_dinheiro (mes_ano, pessoa, descricao, categoria, tipo_debito, valor) VALUES (:mes_ano, :p, :desc, :cat, :td, :val)"),
                             {"mes_ano": mes_ano, "p": str(row['pessoa']), "desc": str(row['descricao']), "cat": str(row['categoria']), "td": str(row['tipo_debito']), "val": float(row['valor'])})

def carregar_caixinha():
    return pd.read_sql(text("SELECT mes_ano, valor FROM caixinha"), engine)

def salvar_caixinha(df_editado):
    with engine.begin() as conn:
        for _, row in df_editado.iterrows():
            mes = row['Mês']
            val = float(row['Aporte do Mês (R$)']) if pd.notnull(row['Aporte do Mês (R$)']) else 0.0
            conn.execute(text("INSERT INTO caixinha (mes_ano, valor) VALUES (:mes, :val) ON CONFLICT (mes_ano) DO UPDATE SET valor = EXCLUDED.valor;"),
                         {"mes": mes, "val": val})

# 8. Cabecalho
col_head, col_logout = st.columns([8, 2])
with col_head:
    st.title("📊 Gestão Financeira Familiar")
with col_logout:
    if st.button("🚪 Sair"):
        st.session_state["autenticado"] = False
        st.rerun()

# 9. Interface Consolidada (3 Abas Principais)
tab1, tab2, tab3 = st.tabs([
    "💳 Cartões & Gastos Individuais",
    "🏠 Contas da Casa & Dinheiro/PIX",
    "⚖️ Fechamento, PIX de Acerto & Caixinha"
])

# --- ABA 1: CARTÕES E GASTOS INDIVIDUAIS ---
with tab1:
    st.header("💳 Renda, Cartões e Fixos Próprios")
    p_sel = st.radio("Selecione a Pessoa:", ["Pessoa 1 (Lucas)", "Pessoa 2 (Marcella)"], horizontal=True)
    pessoa = "Pessoa 1" if "Lucas" in p_sel else "Pessoa 2"

    st.subheader(f"💵 Receitas - {pessoa}")
    df_rec_db = carregar_projecao(pessoa, "RECEITA")
    rows_rec = []
    for item in ESTRUTURA_RECEITAS[pessoa]:
        row_dict = {"Item": item}
        for mes in MESES_PROJECAO:
            val = df_rec_db[(df_rec_db['item'] == item) & (df_rec_db['mes_ano'] == mes)]['valor']
            row_dict[mes] = float(val.iloc[0]) if (not val.empty and pd.notnull(val.iloc[0])) else (12500.0 if item == "Salário Base" else 0.0)
        rows_rec.append(row_dict)
    
    df_rec_edit = st.data_editor(pd.DataFrame(rows_rec), num_rows="fixed", use_container_width=True, key=f"rec_{pessoa}",
                                column_config={m: st.column_config.NumberColumn(m, format="R$ %.2f") for m in MESES_PROJECAO})
    if st.button(f"💾 Salvar Receitas ({pessoa})"):
        salvar_projecao(pessoa, "RECEITA", df_rec_edit)
        st.success("Receitas salvas!")
        st.rerun()

    st.divider()

    st.subheader(f"💳 Faturas de Cartão - {pessoa}")
    df_cart_db = carregar_projecao(pessoa, "CARTAO")
    rows_cart = []
    for item in ESTRUTURA_CARTÕES[pessoa]:
        row_dict = {"Item": item}
        for mes in MESES_PROJECAO:
            val = df_cart_db[(df_cart_db['item'] == item) & (df_cart_db['mes_ano'] == mes)]['valor']
            row_dict[mes] = float(val.iloc[0]) if not val.empty else 0.0
        rows_cart.append(row_dict)
        
    df_cart_edit = st.data_editor(pd.DataFrame(rows_cart), num_rows="fixed", use_container_width=True, key=f"cart_{pessoa}",
                                 column_config={m: st.column_config.NumberColumn(m, format="R$ %.2f") for m in MESES_PROJECAO})
    if st.button(f"💾 Salvar Cartões ({pessoa})"):
        salvar_projecao(pessoa, "CARTAO", df_cart_edit)
        st.success("Cartões salvos!")
        st.rerun()

    st.divider()

    st.subheader(f"📌 Fixos Individuais - {pessoa}")
    df_fixos_edit = st.data_editor(carregar_fixos(pessoa), num_rows="dynamic", use_container_width=True, key=f"fixos_{pessoa}",
                                   column_config={"item": st.column_config.TextColumn("Descrição"), "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")})
    if st.button(f"💾 Salvar Fixos ({pessoa})"):
        salvar_fixos(pessoa, df_fixos_edit)
        st.success("Gastos fixos salvos!")
        st.rerun()

# --- ABA 2: CONTAS DA CASA & DINHEIRO/PIX ---
with tab2:
    st.header("🏡 Contas Compartilhadas da Casa & Lançamentos em Dinheiro/PIX")
    
    st.subheader("🏡 1. Fixos da Casa (Aluguel, Luz, Internet)")
    st.caption("Cadastre as contas recorrentes e quem é o responsável direto por efetuar o pagamento.")
    
    df_comuns_edit = st.data_editor(carregar_comuns(), num_rows="dynamic", use_container_width=True, key="comuns_editor",
                                   column_config={
                                       "item": st.column_config.TextColumn("Descrição da Conta da Casa"),
                                       "valor": st.column_config.NumberColumn("Valor Mensal (R$)", format="R$ %.2f"),
                                       "pagador": st.column_config.SelectboxColumn("Titular do Débito", options=["Pessoa 1", "Pessoa 2"])
                                   })
    if st.button("💾 Salvar Contas da Casa"):
        salvar_comuns(df_comuns_edit)
        st.success("Contas da casa salvas!")
        st.rerun()

    st.divider()

    st.subheader("💸 2. Gastos Pontuais & Compromissos em Dinheiro/PIX")
    
    with st.expander("⚡ Formulário de Lançamento Rápido", expanded=False):
        with st.form("form_rapido"):
            c_p, c_m, c_td, c_v = st.columns(4)
            with c_p: p_r = st.selectbox("Quem pagou?", ["Pessoa 1", "Pessoa 2", "Comum / Casa"])
            with c_m: m_r = st.selectbox("Mês", MESES_PROJECAO)
            with c_td: td_r = st.selectbox("Tipo de Débito", ["Diário (Mês Atual)", "Pré-computado (Próximo Salário)"])
            with c_v: v_r = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
            
            c_cat, c_desc = st.columns([2, 4])
            with c_cat: cat_r = st.selectbox("Categoria", ["Mercado", "Padaria", "Transporte", "Lazer", "Farmácia", "Outros"])
            with c_desc: desc_r = st.text_input("Descrição do Gasto")
            
            if st.form_submit_button("➕ Adicionar Gasto"):
                if desc_r.strip():
                    df_a = carregar_pontuais(m_r)
                    nova_l = pd.DataFrame([{"pessoa": p_r, "descricao": desc_r, "categoria": cat_r, "tipo_debito": td_r, "valor": v_r}])
                    salvar_pontuais(m_r, pd.concat([df_a, nova_l], ignore_index=True))
                    st.success("Gasto registrado!")
                    st.rerun()

    col_m_p, col_b = st.columns([2, 3])
    with col_m_p: mes_p = st.selectbox("Mês para Edição:", MESES_PROJECAO, index=0)
    with col_b: busca_t = st.text_input("🔍 Buscar gasto:")

    df_p_db = carregar_pontuais(mes_p)
    if busca_t: df_p_db = df_p_db[df_p_db['descricao'].str.contains(busca_t, case=False, na=False)]

    df_p_edit = st.data_editor(df_p_db, num_rows="dynamic", use_container_width=True, key="pontuais_editor",
                               column_config={
                                   "pessoa": st.column_config.SelectboxColumn("Pagador", options=["Pessoa 1", "Pessoa 2", "Comum / Casa"]),
                                   "descricao": st.column_config.TextColumn("Descrição"),
                                   "categoria": st.column_config.SelectboxColumn("Categoria", options=["Mercado", "Padaria", "Transporte", "Lazer", "Farmácia", "Outros"]),
                                   "tipo_debito": st.column_config.SelectboxColumn("Natureza do Gasto", options=["Diário (Mês Atual)", "Pré-computado (Próximo Salário)"]),
                                   "valor": st.column_config.NumberColumn("Valor (R$)", format="R$ %.2f")
                               })
    if st.button("💾 Salvar Gastos Pontuais"):
        salvar_pontuais(mes_p, df_p_edit)
        st.success("Gastos salvos!")
        st.rerun()

# --- ABA 3: FECHAMENTO, PIX DE ACERTO & CAIXINHA ---
with tab3:
    st.header("⚖️ Fechamento, PIX de Acerto & Caixinha Acumulativa")
    
    st.subheader("📦 Caixinha de Reserva da Família")
    df_caix_db = carregar_caixinha()
    rows_caix = []
    for m in MESES_PROJECAO:
        v = df_caix_db[df_caix_db['mes_ano'] == m]['valor']
        rows_caix.append({"Mês": m, "Aporte do Mês (R$)": float(v.iloc[0]) if not v.empty else 0.0})
        
    df_caix_edit = st.data_editor(pd.DataFrame(rows_caix), num_rows="fixed", use_container_width=True, key="caix_editor",
                                  column_config={"Mês": st.column_config.TextColumn("Mês", disabled=True),
                                                "Aporte do Mês (R$)": st.column_config.NumberColumn(format="R$ %.2f")})
    if st.button("💾 Salvar Aportes da Caixinha"):
        salvar_caixinha(df_caix_edit)
        st.success("Caixinha atualizada!")
        st.rerun()

    # Cálculo da Caixinha
    acum_caix = 0.0
    d_caix_acum, d_caix_mes = {}, {}
    for _, r in df_caix_edit.iterrows():
        m, val = r['Mês'], float(r['Aporte do Mês (R$)']) if pd.notnull(r['Aporte do Mês (R$)']) else 0.0
        acum_caix += val
        d_caix_mes[m] = val
        d_caix_acum[m] = acum_caix

    # Lógica Completa com PIX de Acerto
    def processar_fechamento():
        rec_p1_all = carregar_projecao("Pessoa 1", "RECEITA")
        rec_p2_all = carregar_projecao("Pessoa 2", "RECEITA")
        cart_p1_all = carregar_projecao("Pessoa 1", "CARTAO")
        cart_p2_all = carregar_projecao("Pessoa 2", "CARTAO")
        fixos_p1_val = carregar_fixos("Pessoa 1")['valor'].sum() if not carregar_fixos("Pessoa 1").empty else 0.0
        fixos_p2_val = carregar_fixos("Pessoa 2")['valor'].sum() if not carregar_fixos("Pessoa 2").empty else 0.0
        df_comuns_data = carregar_comuns()

        totais = {}
        saldo_anterior_fam = 0.0

        for m in MESES_PROJECAO:
            r1 = rec_p1_all[m].sum() if m in rec_p1_all.columns else 12500.0
            r2 = rec_p2_all[m].sum() if m in rec_p2_all.columns else 12500.0
            c1 = cart_p1_all[m].sum() if m in cart_p1_all.columns else 0.0
            c2 = cart_p2_all[m].sum() if m in cart_p2_all.columns else 0.0
            
            df_p = carregar_pontuais(m)
            # Separação por tipo de débito e pagador
            p1_diario = df_p[(df_p['pessoa'] == 'Pessoa 1') & (df_p['tipo_debito'] == 'Diário (Mês Atual)')]['valor'].sum() if not df_p.empty else 0.0
            p2_diario = df_p[(df_p['pessoa'] == 'Pessoa 2') & (df_p['tipo_debito'] == 'Diário (Mês Atual)')]['valor'].sum() if not df_p.empty else 0.0
            
            p1_pre = df_p[(df_p['pessoa'] == 'Pessoa 1') & (df_p['tipo_debito'] != 'Diário (Mês Atual)')]['valor'].sum() if not df_p.empty else 0.0
            p2_pre = df_p[(df_p['pessoa'] == 'Pessoa 2') & (df_p['tipo_debito'] != 'Diário (Mês Atual)')]['valor'].sum() if not df_p.empty else 0.0
            
            com_diario = df_p[(df_p['pessoa'] == 'Comum / Casa') & (df_p['tipo_debito'] == 'Diário (Mês Atual)')]['valor'].sum() if not df_p.empty else 0.0
            com_pre = df_p[(df_p['pessoa'] == 'Comum / Casa') & (df_p['tipo_debito'] != 'Diário (Mês Atual)')]['valor'].sum() if not df_p.empty else 0.0

            # Gastos fixos da casa distribuídos pelo pagador titular
            com_p1 = df_comuns_data[df_comuns_data['pagador'] == 'Pessoa 1']['valor'].sum() if not df_comuns_data.empty else 0.0
            com_p2 = df_comuns_data[df_comuns_data['pagador'] == 'Pessoa 2']['valor'].sum() if not df_comuns_data.empty else 0.0

            # Desembolso Real de Cada Um no Mês
            desembolso_p1 = c1 + fixos_p1_val + com_p1 + p1_diario + p1_pre
            desembolso_p2 = c2 + fixos_p2_val + com_p2 + p2_diario + p2_pre + com_diario + com_pre

            desp_casa_total = com_p1 + com_p2 + com_diario + com_pre
            metade_casa = desp_casa_total / 2.0
            
            # Cálculo do PIX de Acerto
            pago_p1_casa = com_p1
            pago_p2_casa = com_p2 + com_diario + com_pre
            
            diferenca_acerto = pago_p1_casa - metade_casa
            
            caix_m = d_caix_mes.get(m, 0.0)
            rec_fam = r1 + r2
            desp_fam_total = desembolso_p1 + desembolso_p2 + caix_m
            
            sobra_liquida_fam = (rec_fam + saldo_anterior_fam) - desp_fam_total

            totais[m] = {
                "r1": r1, "r2": r2, "rec_fam": rec_fam,
                "desembolso_p1": desembolso_p1, "desembolso_p2": desembolso_p2,
                "desp_casa_total": desp_casa_total, "diferenca_acerto": diferenca_acerto,
                "caix_m": caix_m, "caix_a": d_caix_acum[m],
                "desp_fam_total": desp_fam_total,
                "saldo_anterior_fam": saldo_anterior_fam,
                "sobra_liquida_fam": sobra_liquida_fam
            }
            saldo_anterior_fam = sobra_liquida_fam
            
        return totais

    totais_f = processar_fechamento()

    st.divider()

    st.subheader("📌 Fechamento e PIX de Acerto do Mês")
    mes_f = st.selectbox("Selecione o mês para exame detalhado:", MESES_PROJECAO, index=0)
    tf = totais_f[mes_f]

    # Painel de Compensação (Clearing House)
    dif = tf["diferenca_acerto"]
    if dif > 0:
        st.info(f"🔄 **PIX de Acerto de Contas ({mes_f}):** Marcella (Pessoa 2) deve transferir **R$ {abs(dif):,.2f}** para Lucas (Pessoa 1) para igualar as despesas da casa.")
    elif dif < 0:
        st.info(f"🔄 **PIX de Acerto de Contas ({mes_f}):** Lucas (Pessoa 1) deve transferir **R$ {abs(dif):,.2f}** para Marcella (Pessoa 2) para igualar as despesas da casa.")
    else:
        st.success(f"⚖️ **Contas Equilibradas ({mes_f}):** Ambos pagaram partes iguais das despesas da casa!")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Desembolso Pessoa 1", f"R$ {tf['desembolso_p1']:,.2f}")
    c2.metric("Desembolso Pessoa 2", f"R$ {tf['desembolso_p2']:,.2f}")
    c3.metric("Total Contas da Casa", f"R$ {tf['desp_casa_total']:,.2f}")
    c4.metric("Aporte Caixinha", f"R$ {tf['caix_m']:,.2f}")

    st.divider()

    st.markdown(f"### 📈 Resumo do Saldo da Família ({mes_f})")
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Renda Familiar", f"R$ {tf['rec_fam']:,.2f}")
    mc2.metric("Saldo Mês Anterior (Rollover)", f"R$ {tf['saldo_anterior_fam']:,.2f}")
    
    cor_delta = "normal" if tf['sobra_liquida_fam'] >= 0 else "inverse"
    mc3.metric("Sobra Líquida Acumulada", f"R$ {tf['sobra_liquida_fam']:,.2f}", delta=f"{tf['sobra_liquida_fam']:,.2f}", delta_color=cor_delta)

    st.divider()

    # DASHBOARDS
    st.subheader("📊 Dashboards da Família")
    g1, g2 = st.columns(2)
    with g1:
        fig_p = px.pie(names=['Gasto P1', 'Gasto P2', 'Caixinha'], 
                       values=[tf['desembolso_p1'], tf['desembolso_p2'], tf['caix_m']], 
                       title=f"Proporção de Desembolso ({mes_f})", hole=0.4)
        st.plotly_chart(fig_p, use_container_width=True)
    with g2:
        df_cx = pd.DataFrame([{"Mês": m, "Saldo Caixinha": totais_f[m]["caix_a"]} for m in MESES_PROJECAO])
        fig_l = px.line(df_cx, x="Mês", y="Saldo Caixinha", title="Evolução da Caixinha (R$)", markers=True)
        fig_l.update_traces(fill='tozeroy')
        st.plotly_chart(fig_l, use_container_width=True)

    st.divider()

    # TABELA EVOLUTIVA FINAL
    st.subheader("📅 Tabela de Projeção Evolutiva (2026 - 2030)")
    
    r_ant = {"Métrica": "1. Saldo do Mês Anterior"}
    r_rec = {"Métrica": "2. Renda Total Família"}
    r_dp1 = {"Métrica": "3. Desembolso Pessoa 1"}
    r_dp2 = {"Métrica": "4. Desembolso Pessoa 2"}
    r_caix_m = {"Métrica": "5. Aporte Caixinha (Mês)"}
    r_desp_t = {"Métrica": "6. Despesa Total Família"}
    r_sobra = {"Métrica": "7. Sobra Final Acumulada"}
    r_caix_a = {"Métrica": "8. Caixinha Acumulada"}

    for m in MESES_PROJECAO:
        t = totais_f[m]
        r_ant[m] = t["saldo_anterior_fam"]
        r_rec[m] = t["rec_fam"]
        r_dp1[m] = t["desembolso_p1"]
        r_dp2[m] = t["desembolso_p2"]
        r_caix_m[m] = t["caix_m"]
        r_desp_t[m] = t["desp_fam_total"]
        r_sobra[m] = t["sobra_liquida_fam"]
        r_caix_a[m] = t["caix_a"]

    df_final = pd.DataFrame([r_ant, r_rec, r_dp1, r_dp2, r_caix_m, r_desp_t, r_sobra, r_caix_a])
    st.dataframe(df_final, use_container_width=True, column_config={m: st.column_config.NumberColumn(format="R$ %.2f") for m in MESES_PROJECAO})

    # Download Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_final.to_excel(writer, sheet_name='Projecao_Financeira', index=False)
    
    st.download_button(
        label="📥 Baixar Projeção Completa em Excel (.xlsx)",
        data=output.getvalue(),
        file_name="Projecao_Financeira_Familiar.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
