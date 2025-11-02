import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
from io import BytesIO
import bcrypt

# ====================================
# CONFIGURAÇÃO DA PÁGINA
# ====================================
st.set_page_config(page_title="Controle de Produção e Desperdício", page_icon="🏭", layout="wide")

# ====================================
# CONEXÃO COM SUPABASE
# ====================================
@st.cache_resource
def conectar_supabase() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)

supabase = conectar_supabase()

# ====================================
# FUNÇÕES AUXILIARES
# ====================================
def cor_do_dia(dia_semana):
    cores = ["azul", "verde", "amarelo", "laranja", "vermelho", "prata", "dourado"]
    return cores[dia_semana]

def emoji_cor(cor):
    mapa = {"azul": "🟦", "verde": "🟩", "amarelo": "🟨", "laranja": "🟧",
            "vermelho": "🟥", "prata": "⬜", "dourado": "🟨✨"}
    return mapa.get(cor, "⬛")

def hash_senha(senha):
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verificar_senha(senha_digitada, senha_hash):
    try:
        return bcrypt.checkpw(senha_digitada.encode("utf-8"), senha_hash.encode("utf-8"))
    except Exception:
        return False

# ====================================
# LOGIN
# ====================================
def login_page():
    st.title("🔐 Login no Sistema")

    try:
        usuarios = supabase.table("usuarios").select("*").execute().data
        df_users = pd.DataFrame(usuarios)
    except Exception as e:
        st.error(f"❌ Erro ao conectar com o banco: {e}")
        return

    if df_users.empty:
        st.warning("⚠️ Nenhum usuário cadastrado. Cadastre pelo painel do Supabase.")
        return

    usuario = st.text_input("Usuário:")
    senha = st.text_input("Senha:", type="password")

    if st.button("Entrar"):
        user = df_users[df_users["usuario"].str.lower() == usuario.strip().lower()]
        if not user.empty and verificar_senha(senha, user.iloc[0]["senha"]):
            st.session_state["logado"] = True
            st.session_state["usuario"] = user.iloc[0]["usuario"]
            st.session_state["tipo"] = user.iloc[0].get("tipo", "usuario")
            st.session_state["nome"] = user.iloc[0].get("nome", "Usuário")
            st.success(f"Bem-vindo(a), {st.session_state['nome']} 👋")
            st.rerun()
        else:
            st.error("❌ Usuário ou senha incorretos.")

# ====================================
# APP PRINCIPAL
# ====================================
def main_app():
    st.sidebar.markdown(f"👤 Usuário: **{st.session_state['usuario']}**")
    st.sidebar.markdown(f"🔐 Tipo: **{st.session_state['tipo']}**")

    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    menu = st.sidebar.radio(
        "Menu principal:",
        [
            "📊 Painel de Status",
            "Registrar Produção 🧁",
            "Registrar Desperdício ⚠️",
            "♻️ Remarcar Produtos",
            "📈 Relatórios",
            "📤 Exportar",
            "👥 Gerenciar Usuários",
            "🧹 Zerar Sistema"
        ]
    )

    # ====================================
    # ALERTAS NA BARRA LATERAL
    # ====================================
    st.sidebar.markdown("### 🔔 Alertas de Validade")
    try:
        dados_alertas = supabase.table("producao").select("*").execute().data
        df_alertas = pd.DataFrame(dados_alertas)
        if not df_alertas.empty:
            df_alertas["data_validade"] = pd.to_datetime(df_alertas["data_validade"], errors="coerce")
            hoje = datetime.now().date()
            df_alertas["dias"] = df_alertas["data_validade"].apply(
                lambda x: (x.date() - hoje).days if pd.notnull(x) else None
            )
            vencendo = df_alertas[df_alertas["dias"].between(0, 2, inclusive="both")]
            vencidos = df_alertas[df_alertas["dias"] < 0]

            for _, row in vencendo.iterrows():
                st.sidebar.warning(f"⚠️ {row['produto']} ({row['cor']}) — vence em {row['dias']} dia(s)")
            for _, row in vencidos.iterrows():
                st.sidebar.error(f"❌ {row['produto']} ({row['cor']}) — VENCIDO!")
        else:
            st.sidebar.info("Nenhum produto cadastrado.")
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar alertas: {e}")

    # ====================================
    # PAINEL DE STATUS (com filtro de data)
    # ====================================
    if menu == "📊 Painel de Status":
        st.header("📊 Situação Atual de Produção")

        try:
            dados = supabase.table("producao").select("*").execute().data
            producao = pd.DataFrame(dados)
        except Exception as e:
            st.error(f"❌ Erro ao carregar dados: {e}")
            st.stop()

        if producao.empty:
            st.info("Nenhum produto cadastrado ainda.")
        else:
            st.subheader("🗓️ Filtrar por intervalo de datas")
            col1, col2 = st.columns(2)
            with col1:
                data_inicio = st.date_input("Data inicial", datetime.now().date() - timedelta(days=7))
            with col2:
                data_fim = st.date_input("Data final", datetime.now().date())

            producao["data_producao"] = pd.to_datetime(producao["data_producao"], errors="coerce")
            mask = (producao["data_producao"].dt.date >= data_inicio) & (producao["data_producao"].dt.date <= data_fim)
            producao_filtrada = producao.loc[mask]

            if producao_filtrada.empty:
                st.warning("⚠️ Nenhum registro encontrado no período selecionado.")
            else:
                producao_filtrada["data_validade"] = pd.to_datetime(producao_filtrada["data_validade"], errors="coerce")
                hoje = datetime.now().date()
                producao_filtrada["dias_restantes"] = producao_filtrada["data_validade"].apply(
                    lambda x: (x.date() - hoje).days if pd.notnull(x) else None
                )

                def status_vencimento(dias):
                    if dias is None:
                        return "❓ Sem data"
                    elif dias > 2:
                        return "✅ Dentro do prazo"
                    elif 0 < dias <= 2:
                        return "⚠️ Perto do vencimento"
                    else:
                        return "❌ Vencido"

                producao_filtrada["status"] = producao_filtrada["dias_restantes"].apply(status_vencimento)

                st.dataframe(
                    producao_filtrada[["id", "produto", "cor", "data_producao", "data_validade", "dias_restantes", "status"]]
                )

                col1, col2, col3 = st.columns(3)
                total = len(producao_filtrada)
                vencidos = len(producao_filtrada[producao_filtrada["status"].str.contains("Vencido")])
                perto = len(producao_filtrada[producao_filtrada["status"].str.contains("Perto")])
                col1.metric("🧁 Total de Produtos", total)
                col2.metric("⚠️ Perto do Vencimento", perto)
                col3.metric("❌ Vencidos", vencidos)

    # ====================================
    # RELATÓRIOS (com filtro de data)
    # ====================================
    elif menu == "📈 Relatórios":
        st.header("📈 Relatórios de Produção e Desperdício")

        aba = st.radio("Escolha o tipo de relatório:", ["Produção", "Desperdício"])
        st.subheader("🗓️ Filtrar por intervalo de datas")
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data inicial", datetime.now().date() - timedelta(days=7), key="inicio_rel")
        with col2:
            data_fim = st.date_input("Data final", datetime.now().date(), key="fim_rel")

        if aba == "Produção":
            producao = pd.DataFrame(supabase.table("producao").select("*").execute().data)
            if producao.empty:
                st.info("Nenhuma produção registrada.")
            else:
                producao["data_producao"] = pd.to_datetime(producao["data_producao"], errors="coerce")
                mask = (producao["data_producao"].dt.date >= data_inicio) & (producao["data_producao"].dt.date <= data_fim)
                df_prod = producao.loc[mask]

                if df_prod.empty:
                    st.warning("⚠️ Nenhum registro encontrado nesse período.")
                else:
                    df_resumo = df_prod.groupby("produto")["quantidade_produzida"].sum().reset_index()
                    st.dataframe(df_resumo)
                    st.bar_chart(df_resumo.set_index("produto"))

        elif aba == "Desperdício":
            desperdicio = pd.DataFrame(supabase.table("desperdicio").select("*").execute().data)
            if desperdicio.empty:
                st.info("Nenhum desperdício registrado.")
            else:
                desperdicio["data_desperdicio"] = pd.to_datetime(desperdicio["data_desperdicio"], errors="coerce")
                mask = (desperdicio["data_desperdicio"].dt.date >= data_inicio) & (desperdicio["data_desperdicio"].dt.date <= data_fim)
                df_desp = desperdicio.loc[mask]

                if df_desp.empty:
                    st.warning("⚠️ Nenhum registro encontrado nesse período.")
                else:
                    df_resumo = df_desp.groupby("produto")["quantidade_desperdicada"].sum().reset_index()
                    st.dataframe(df_resumo)
                    st.bar_chart(df_resumo.set_index("produto"))

    # ====================================
    # EXPORTAR RELATÓRIOS (filtrados)
    # ====================================
    elif menu == "📤 Exportar":
        st.header("📤 Exportar Dados Filtrados por Data")

        aba = st.radio("Escolha o tipo de dado para exportar:", ["Produção", "Desperdício"])
        formato = st.radio("Formato do arquivo:", ["Excel (.xlsx)", "CSV (.csv)"])
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data inicial", datetime.now().date() - timedelta(days=7), key="inicio_exp")
        with col2:
            data_fim = st.date_input("Data final", datetime.now().date(), key="fim_exp")

        tabela = "producao" if aba == "Produção" else "desperdicio"
        dados = supabase.table(tabela).select("*").execute().data
        df = pd.DataFrame(dados)

        if df.empty:
            st.warning(f"⚠️ Nenhum dado encontrado na tabela '{tabela}'.")
        else:
            campo_data = "data_producao" if aba == "Produção" else "data_desperdicio"
            df[campo_data] = pd.to_datetime(df[campo_data], errors="coerce")
            mask = (df[campo_data].dt.date >= data_inicio) & (df[campo_data].dt.date <= data_fim)
            df_filtrado = df.loc[mask]

            if df_filtrado.empty:
                st.warning("⚠️ Nenhum registro nesse período.")
            else:
                nome_arquivo = f"{tabela}_{data_inicio}_{data_fim}.xlsx"
                if formato == "Excel (.xlsx)":
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                        df_filtrado.to_excel(writer, index=False, sheet_name=tabela.capitalize())
                    st.download_button("📥 Baixar Excel", data=buffer.getvalue(),
                                       file_name=nome_arquivo,
                                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    csv = df_filtrado.to_csv(index=False).encode("utf-8")
                    st.download_button("📥 Baixar CSV", data=csv,
                                       file_name=f"{tabela}_{data_inicio}_{data_fim}.csv", mime="text/csv")
# ====================================
# EXECUÇÃO
# ====================================
if "logado" not in st.session_state or not st.session_state["logado"]:
    login_page()
else:
    main_app()
