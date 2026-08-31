import os
import io
import streamlit as st
import pandas as pd
import plotly.express as px
from sqlalchemy import create_engine, text

# 1. Configuração da Página
st.set_page_config(page_title="Sistema Integrado de Gestão Financeira", layout="wide")

# 2. Injeção de CSS para Otimização Mobile
st.markdown("""
    <style>
        .block-container {
            padding-top: 1.2rem !important;
            padding-bottom: 1.5rem !important;
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }
        @media (max-width: 640px) {
            h1 { font-size: 1.5rem !important; }
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

# 4. Conexão com o Banco de Dados Supabase (PostgreSQL)
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

init_db()

# 6. Constantes e Estruturas Dinâmicas (Projeção até 2030)
def gerar_meses_projecao(ano_inicio=2026, mes_inicio=8, ano_fim=2030, mes_fim=12):
    meses = []
    for ano in range(ano_inicio, ano_fim + 1):
        m_start = mes_inicio if ano == ano_inicio else 1
        m_end = mes_fim if ano == ano_fim else 12
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

# 7. Funções de Persistência
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

def carregar_comuns():
    query = "SELECT id, item, valor FROM gastos_comuns"
    return pd.read_sql(text(query), engine)

def salvar_comuns(df_editado):
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM gastos_comuns"))
        for _, row in df_editado.iterrows():
            if str(row['item']).strip():
                query = "INSERT INTO gastos_comuns (item, valor) VALUES (:item, :val)"
                conn.execute(text(query), {"item": str(row['item']), "val": float(row['valor'])})

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

def carregar_caixinha():
    query = "SELECT mes_ano, valor FROM caixinha"
    return pd.read_sql(text(query), engine)

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

# 8. Cabeçalho e Logout
col_head, col_logout = st.columns([8, 2])
with col_head:
    st.title("📊 Painel Financeiro Integrado & Projeção")
with col_logout:
    if st.button("🚪 Sair"):
        st.session_state["autenticado"] = False
        st.rerun()

# 9. Interface Principal (Abas)
tab_p1, tab_p2, tab_comuns, tab_pontuais, tab_consolidado = st.tabs([
    "👤 Pessoa 1 (Lucas)", 
    "👤 Pessoa 2 (Marcella)", 
    "🏡 Despesas Comuns (Casa/Aluguel)",
    "💸 Gastos Pontuais (Dinheiro/PIX)",
    "🏠 Visão Consolidada, Gráficos & Caixinha"
])

def renderizar_pessoa(pessoa):
    st.subheader("💵 1. Receitas (Salário e Rendimentos)")
    df_rec_db = carregar_projecao(pessoa, "RECEITA")
    rows_rec = []
    
    for item in ESTRUTURA_RECEITAS[pessoa]:
        row_dict = {"Item": item}
        for mes in MESES_PROJECAO:
            val = df_rec_db[(df_rec_db['item'] == item) & (df_rec_db['mes_ano'] == mes)]['valor']
            
            # Lê o valor gravado individualmente para o mês.
            # Se a célula não tiver registro, usa o valor de partida de R$ 12.500,00.
            if not val.empty and pd.notnull(val.iloc[0]):
                row_dict[mes] = float(val.iloc[0])
            else:
                row_dict[mes] = 12500.0 if item == "Salário Base" else 0.0
                
        rows_rec.append(row_dict)
    
    df_rec_grid = pd.DataFrame(rows_rec)
    df_rec_edit = st.data_editor(
        df_rec_grid, num_rows="fixed", use_container_width=True, key=f"rec_{pessoa}",
        column_config={mes: st.column_config.NumberColumn(f"{mes}", format="R$ %.2f", min_value=0.0) for mes in MESES_PROJECAO}
    )
    if st.button(f"💾 Salvar Receitas - {pessoa}"):
        salvar_projecao(pessoa, "RECEITA", df_rec_edit)
        st.success("Receitas salvas individualmente com sucesso!")
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
        st.success("Cartões salvos com sucesso!")
        st.rerun()

    st.divider()

    st.subheader("📌 3. Gastos Fixos Individuais Recorrentes")
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

    return df_rec_edit, df_cart_edit, df_fixos_edit

with tab_p1:
    rec_p1, cart_p1, fixos_p1 = renderizar_pessoa("Pessoa 1")

with tab_p2:
    rec_p2, cart_p2, fixos_p2 = renderizar_pessoa("Pessoa 2")

with tab_comuns:
    st.header("🏡 Despesas Comuns do Casal / Casa")
    st.info("Cadastre aqui as despesas compartilhadas (ex: Aluguel, Condomínio, Energia, Água, Internet, Mercado da Casa).")
    
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
    st.header("💸 Gastos Pontuais em Dinheiro/PIX")
    
    with st.expander("⚡ Formulário de Lançamento Rápido (Celular)", expanded=False):
        with st.form("form_rapido"):
            c_p, c_m, c_c, c_v = st.columns(4)
            with c_p:
                p_rapida = st.selectbox("Pessoa", ["Pessoa 1", "Pessoa 2", "Comum / Casa"])
            with c_m:
                m_rapido = st.selectbox("Mês", MESES_PROJECAO)
            with c_c:
                cat_rapida = st.selectbox("Categoria", ["Mercado", "Padaria", "Transporte", "Lazer", "Farmácia", "Outros"])
            with c_v:
                val_rapido = st.number_input("Valor (R$)", min_value=0.0, step=10.0)
            
            desc_rapida = st.text_input("Descrição do Gasto")
            if st.form_submit_button("➕ Adicionar Gasto"):
                if desc_rapida.strip():
                    df_atual = carregar_pontuais(m_rapido)
                    nova_linha = pd.DataFrame([{"pessoa": p_rapida, "descricao": desc_rapida, "categoria": cat_rapida, "valor": val_rapido}])
                    df_novo = pd.concat([df_atual, nova_linha], ignore_index=True)
                    salvar_pontuais(m_rapido, df_novo)
                    st.success("Gasto adicionado!")
                    st.rerun()
                else:
                    st.warning("Preencha a descrição!")

    st.divider()

    col_sel_p, col_busca = st.columns([2, 3])
    with col_sel_p:
        mes_pontual = st.selectbox("Selecione o Mês para Edição:", MESES_PROJECAO, index=0)
    with col_busca:
        termo_busca = st.text_input("🔍 Pesquisar gasto por palavra-chave:")

    df_pontuais_db = carregar_pontuais(mes_pontual)
    if termo_busca:
        df_pontuais_db = df_pontuais_db[df_pontuais_db['descricao'].str.contains(termo_busca, case=False, na=False)]

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
        st.success("Aportes salvos com sucesso!")
        st.rerun()

    acumulado_caixinha = 0.0
    dict_caixinha_acum = {}
    dict_caixinha_mes = {}
    for _, row in df_caixinha_edit.iterrows():
        m = row['Mês']
        v = float(row['Aporte do Mês (R$)']) if pd.notnull(row['Aporte do Mês (R$)']) else 0.0
        acumulado_caixinha += v
        dict_caixinha_mes[m] = v
        dict_caixinha_acum[m] = acumulado_caixinha

    st.divider()

    total_comuns_fixos = df_comuns_edit['valor'].sum() if not df_comuns_edit.empty else 0.0

    def calcular_projecao_completa():
        dados_meses = {}
        saldo_anterior = 0.0
        
        for mes in MESES_PROJECAO:
            r1 = rec_p1[mes].sum()
            c1 = cart_p1[mes].sum()
            f1 = fixos_p1['valor'].sum()
            
            r2 = rec_p2[mes].sum()
            c2 = cart_p2[mes].sum()
            f2 = fixos_p2['valor'].sum()
            
            df_p = carregar_pontuais(mes)
            p1 = df_p[df_p['pessoa'] == 'Pessoa 1']['valor'].sum() if not df_p.empty else 0.0
            p2 = df_p[df_p['pessoa'] == 'Pessoa 2']['valor'].sum() if not df_p.empty else 0.0
            p_com = df_p[df_p['pessoa'] == 'Comum / Casa']['valor'].sum() if not df_p.empty else 0.0
            
            dp1 = c1 + f1 + p1
            dp2 = c2 + f2 + p2
            dcom = total_comuns_fixos + p_com
            c_mes = dict_caixinha_mes.get(mes, 0.0)
            
            rec_total = r1 + r2
            desp_base = dp1 + dp2 + dcom + c_mes
            
            disponivel_total = rec_total + saldo_anterior
            sobra_liquida = disponivel_total - desp_base
            
            dados_meses[mes] = {
                "rec_p1": r1, "desp_p1": dp1,
                "rec_p2": r2, "desp_p2": dp2,
                "desp_comum": dcom,
                "caixinha_mes": c_mes,
                "caixinha_acum": dict_caixinha_acum[mes],
                "rec_total": rec_total,
                "desp_base": desp_base,
                "saldo_anterior": saldo_anterior,
                "disponivel_total": disponivel_total,
                "sobra_liquida": sobra_liquida
            }
            saldo_anterior = sobra_liquida
            
        return dados_meses

    totais_gerais = calcular_projecao_completa()

    st.subheader("📌 Análise Detalhada & Saúde Financeira do Mês")
    mes_foco = st.selectbox("Selecione o mês para examinar:", MESES_PROJECAO, index=0)
    tf = totais_gerais[mes_foco]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"**Pessoa 1 ({mes_foco})**")
        st.metric("Receita", f"R$ {tf['rec_p1']:,.2f}")
        st.metric("Gastos Próprios", f"R$ {tf['desp_p1']:,.2f}")
    with c2:
        st.markdown(f"**Pessoa 2 ({mes_foco})**")
        st.metric("Receita", f"R$ {tf['rec_p2']:,.2f}")
        st.metric("Gastos Próprios", f"R$ {tf['desp_p2']:,.2f}")
    with c3:
        st.markdown(f"**Despesas Casa & Caixinha**")
        st.metric("Total Casa", f"R$ {tf['desp_comum']:,.2f}")
        st.metric("Aporte Caixinha", f"R$ {tf['caixinha_mes']:,.2f}")
    with c4:
        st.markdown(f"**RESUMO COM ROLLOVER**")
        st.metric("Saldo Mês Anterior", f"R$ {tf['saldo_anterior']:,.2f}")
        st.metric("Despesa Total", f"R$ {tf['desp_base']:,.2f}")
        
        cor_sobra = "normal" if tf['sobra_liquida'] >= 0 else "inverse"
        st.metric("Sobra Final Acumulada", f"R$ {tf['sobra_liquida']:,.2f}", delta=f"{tf['sobra_liquida']:,.2f}", delta_color=cor_sobra)

    taxa_poupanca = (tf['caixinha_mes'] / tf['rec_total'] * 100) if tf['rec_total'] > 0 else 0
    st.progress(min(int(taxa_poupanca), 100), text=f"📊 Taxa de Poupança do Mês: {taxa_poupanca:.1f}% da Renda direcionada à Caixinha")

    st.divider()

    with st.expander("⚖️ Simulador de Divisão Justa das Despesas Comuns", expanded=False):
        if tf['rec_total'] > 0:
            prop_p1 = (tf['rec_p1'] / tf['rec_total']) * 100
            prop_p2 = (tf['rec_p2'] / tf['rec_total']) * 100
            pago_p1 = tf['desp_comum'] * (prop_p1 / 100)
            pago_p2 = tf['desp_comum'] * (prop_p2 / 100)
            
            st.write(f"Proporção de Renda: **Pessoa 1 ({prop_p1:.1f}%)** | **Pessoa 2 ({prop_p2:.1f}%)**")
            col_div1, col_div2 = st.columns(2)
            col_div1.metric("Pessoa 1 paga das Despesas Comuns:", f"R$ {pago_p1:,.2f}")
            col_div2.metric("Pessoa 2 paga das Despesas Comuns:", f"R$ {pago_p2:,.2f}")
        else:
            st.info("Insira as receitas para calcular a divisão proporcional.")

    st.divider()

    st.subheader("📊 Dashboards Visuais Interativos")
    g_col1, g_col2 = st.columns(2)

    with g_col1:
        labels_pie = ['Gastos P1', 'Gastos P2', 'Despesas Casa', 'Caixinha']
        values_pie = [tf['desp_p1'], tf['desp_p2'], tf['desp_comum'], tf['caixinha_mes']]
        fig_pie = px.pie(names=labels_pie, values=values_pie, title=f"Distribuição de Gastos ({mes_foco})", hole=0.4)
        st.plotly_chart(fig_pie, use_container_width=True)

    with g_col2:
        df_chart_caixinha = pd.DataFrame([{"Mês": m, "Saldo Acumulado": totais_gerais[m]["caixinha_acum"]} for m in MESES_PROJECAO])
        fig_line = px.line(df_chart_caixinha, x="Mês", y="Saldo Acumulado", title="Evolução Patrimonial da Caixinha (R$)", markers=True)
        fig_line.update_traces(fill='tozeroy')
        st.plotly_chart(fig_line, use_container_width=True)

    list_barras = []
    for m in MESES_PROJECAO:
        list_barras.append({"Mês": m, "Tipo": "Renda Familiar", "Valor": totais_gerais[m]["rec_total"]})
        list_barras.append({"Mês": m, "Tipo": "Despesa Total", "Valor": totais_gerais[m]["desp_base"]})
    df_barras = pd.DataFrame(list_barras)
    fig_bar = px.bar(df_barras, x="Mês", y="Valor", color="Tipo", barmode="group", title="Comparativo Renda vs. Despesa Mês a Mês")
    st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    st.subheader("📅 Tabela de Projeção Evolutiva com Saldo Acumulado (Rollover)")
    
    r_ant = {"Métrica": "1. Saldo do Mês Anterior"}
    r_rec = {"Métrica": "2. Renda Total do Mês"}
    r_p1 = {"Métrica": "3. Gastos Próprios - Pessoa 1"}
    r_p2 = {"Métrica": "4. Gastos Próprios - Pessoa 2"}
    r_com = {"Métrica": "5. Despesas Comuns (Casa)"}
    r_caix_m = {"Métrica": "6. Aporte Caixinha (Mês)"}
    r_desp = {"Métrica": "7. Despesa Total do Mês"}
    r_sobra = {"Métrica": "8. Sobra Final Acumulada"}
    r_caix_a = {"Métrica": "9. Caixinha Saldo Acumulado"}
    
    for m in MESES_PROJECAO:
        t = totais_gerais[m]
        r_ant[m] = t["saldo_anterior"]
        r_rec[m] = t["rec_total"]
        r_p1[m] = t["desp_p1"]
        r_p2[m] = t["desp_p2"]
        r_com[m] = t["desp_comum"]
        r_caix_m[m] = t["caixinha_mes"]
        r_desp[m] = t["desp_base"]
        r_sobra[m] = t["sobra_liquida"]
        r_caix_a[m] = t["caixinha_acum"]
        
    df_resumo_final = pd.DataFrame([r_ant, r_rec, r_p1, r_p2, r_com, r_caix_m, r_desp, r_sobra, r_caix_a])
    cols_conf = {m: st.column_config.NumberColumn(format="R$ %.2f") for m in MESES_PROJECAO}
    st.dataframe(df_resumo_final, use_container_width=True, column_config=cols_conf)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_resumo_final.to_excel(writer, sheet_name='Projecao_Financeira', index=False)
    
    st.download_button(
        label="📥 Baixar Projeção Completa em Excel (.xlsx)",
        data=output.getvalue(),
        file_name="Projecao_Financeira_Familiar.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
