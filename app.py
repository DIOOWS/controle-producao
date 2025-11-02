import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client

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

def dia_da_cor(cor):
    mapa = {
        "azul": "Segunda-feira", "verde": "Terça-feira", "amarelo": "Quarta-feira",
        "laranja": "Quinta-feira", "vermelho": "Sexta-feira",
        "prata": "Sábado", "dourado": "Domingo"
    }
    return mapa.get(cor, "?")

def emoji_cor(cor):
    mapa = {"azul": "🟦", "verde": "🟩", "amarelo": "🟨", "laranja": "🟧",
            "vermelho": "🟥", "prata": "⬜", "dourado": "🟨✨"}
    return mapa.get(cor, "⬛")

# ====================================
# LOGIN
# ====================================
def login_page():
    st.title("🔐 Login no Sistema")

    # Testa conexão com Supabase
    try:
        usuarios = supabase.table("usuarios").select("*").execute().data
        df_users = pd.DataFrame(usuarios)
    except Exception as e:
        st.error(f"❌ Erro ao conectar com o banco: {e}")
        return

    if df_users.empty:
        st.warning("⚠️ Nenhum usuário cadastrado no banco. Cadastre pelo painel do Supabase.")
        return

    usuario = st.text_input("Usuário:")
    senha = st.text_input("Senha:", type="password")

    if st.button("Entrar"):
        # Verifica se o usuário existe
        user = df_users[
            (df_users["usuario"].str.strip().str.lower() == usuario.strip().lower())
            & (df_users["senha"].astype(str).str.strip() == senha.strip())
        ]

        if not user.empty:
            st.session_state["logado"] = True
            st.session_state["usuario"] = user.iloc[0]["usuario"]
            st.session_state["tipo"] = user.iloc[0].get("tipo", "usuario")
            nome = user.iloc[0].get("nome", "Usuário")

            st.success(f"Bem-vindo(a), {nome}! 👋")
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
        ["📊 Painel de Status", "Registrar Produção 🧁", "Registrar Desperdício ⚠️", "📈 Relatórios", "📤 Exportar", "🧹 Zerar Sistema"]
    )

    # ====================================
    # PRODUÇÃO
    # ====================================
    if menu == "Registrar Produção 🧁":
        st.header("🧁 Registrar Produção")
        produto = st.text_input("Produto:")
        quantidade = st.number_input("Quantidade produzida:", min_value=1, step=1)
        if st.button("💾 Salvar Produção"):
            if produto.strip() == "":
                st.error("Digite o nome do produto.")
            else:
                data = datetime.now()
                cor = cor_do_dia(data.weekday())
                validade = (data + timedelta(days=2)).strftime("%Y-%m-%d")
                supabase.table("producao").insert({
                    "data_producao": data.strftime("%Y-%m-%d"),
                    "produto": produto,
                    "cor": cor,
                    "quantidade_produzida": quantidade,
                    "data_remarcacao": None,
                    "data_validade": validade
                }).execute()
                st.success(f"✅ Produção salva ({emoji_cor(cor)} {cor.upper()})")

    # ====================================
    # DESPERDÍCIO
    # ====================================
    elif menu == "Registrar Desperdício ⚠️":
        st.header("⚠️ Registrar Desperdício")
        dados = supabase.table("producao").select("*").execute().data
        df = pd.DataFrame(dados)
        if df.empty:
            st.info("Nenhum produto cadastrado.")
        else:
            produto = st.selectbox("Selecione o produto:", df["produto"].unique())
            quantidade = st.number_input("Quantidade desperdiçada:", min_value=1, step=1)
            motivo = st.text_area("Motivo do desperdício:")
            if st.button("💾 Registrar Desperdício"):
                sel = df[df["produto"] == produto].iloc[0]
                supabase.table("desperdicio").insert({
                    "data_desperdicio": datetime.now().strftime("%Y-%m-%d"),
                    "produto": produto,
                    "cor": sel["cor"],
                    "quantidade_desperdicada": quantidade,
                    "motivo": motivo,
                    "id_producao": sel["id"],
                    "data_producao": sel["data_producao"]
                }).execute()
                st.success("✅ Desperdício registrado!")

    # ====================================
    # RELATÓRIOS
    # ====================================
    elif menu == "📈 Relatórios":
        st.header("📈 Relatórios de Produção e Desperdício")
        producao = pd.DataFrame(supabase.table("producao").select("*").execute().data)
        desperdicio = pd.DataFrame(supabase.table("desperdicio").select("*").execute().data)

        aba = st.radio("Escolha o tipo de relatório:", ["Produção", "Desperdício"])

        if aba == "Produção" and not producao.empty:
            df_prod = producao.groupby("produto")["quantidade_produzida"].sum().reset_index()
            st.dataframe(df_prod)
            st.bar_chart(df_prod.set_index("produto"))
        elif aba == "Desperdício" and not desperdicio.empty:
            df_desp = desperdicio.groupby("produto")["quantidade_desperdicada"].sum().reset_index()
            st.dataframe(df_desp)
            st.bar_chart(df_desp.set_index("produto"))
        else:
            st.info("Sem dados para exibir.")

    # ====================================
    # EXPORTAR
    # ====================================
    elif menu == "📤 Exportar":
        st.header("📤 Exportar dados")
        aba = st.radio("Escolha:", ["Produção", "Desperdício"])
        df = pd.DataFrame(supabase.table(aba.lower()).select("*").execute().data)
        if df.empty:
            st.warning("Nenhum dado disponível.")
        else:
            csv = df.to_csv(index=False).encode("utf-8")
            st.download_button("📥 Baixar CSV", data=csv, file_name=f"{aba.lower()}.csv", mime="text/csv")

    # ====================================
    # ZERAR
    # ====================================
    elif menu == "🧹 Zerar Sistema":
        st.header("🧹 Limpar Tabelas")
        if st.session_state["tipo"] != "admin":
            st.warning("⚠️ Apenas o ADMIN pode zerar o sistema.")
        else:
            if st.button("🚨 Apagar tudo"):
                supabase.table("producao").delete().neq("id", 0).execute()
                supabase.table("desperdicio").delete().neq("id", 0).execute()
                st.success("✅ Dados apagados com sucesso!")

# ====================================
# EXECUÇÃO
# ====================================
if "logado" not in st.session_state or not st.session_state["logado"]:
    login_page()
else:
    main_app()
