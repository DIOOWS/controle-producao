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
            "📈 Relatórios",
            "📤 Exportar"
        ]
    )

    # ====================================
    # REGISTRAR PRODUÇÃO
    # ====================================
    if menu == "Registrar Produção 🧁":
        st.header("🧁 Registrar Produção")
        produto = st.text_input("Produto:")
        quantidade = st.number_input("Quantidade produzida:", min_value=1, step=1)

        if st.button("💾 Salvar Produção"):
            if not produto.strip():
                st.error("Digite o nome do produto.")
            else:
                data = datetime.now()
                cor = cor_do_dia(data.weekday())
                validade = (data + timedelta(days=2)).strftime("%Y-%m-%d")

                try:
                    supabase.table("producao").insert({
                        "data_producao": data.strftime("%Y-%m-%d"),
                        "produto": produto.strip(),
                        "cor": cor,
                        "quantidade_produzida": quantidade,
                        "data_remarcacao": None,
                        "data_validade": validade
                    }).execute()
                    st.success(f"✅ Produção salva com sucesso ({emoji_cor(cor)} {cor.upper()})")
                except Exception as e:
                    st.error(f"❌ Erro ao salvar produção: {e}")

        st.divider()
        st.subheader("📋 Produções recentes")
        try:
            dados = supabase.table("producao").select("*").order("id", desc=True).limit(10).execute().data
            df = pd.DataFrame(dados)
            if not df.empty:
                st.dataframe(df)
            else:
                st.info("Nenhuma produção registrada ainda.")
        except Exception as e:
            st.error(f"Erro ao carregar produções: {e}")

    # ====================================
    # REGISTRAR DESPERDÍCIO
    # ====================================
    elif menu == "Registrar Desperdício ⚠️":
        st.header("⚠️ Registrar Desperdício")
        try:
            dados = supabase.table("producao").select("*").execute().data
            producao = pd.DataFrame(dados)
        except Exception as e:
            st.error(f"Erro ao carregar produções: {e}")
            return

        if producao.empty:
            st.info("Nenhum produto disponível para marcar desperdício.")
        else:
            produto = st.selectbox("Selecione o produto:", producao["produto"].unique())
            quantidade = st.number_input("Quantidade desperdiçada:", min_value=1, step=1)
            motivo = st.text_area("Motivo do desperdício:")

            if st.button("💾 Registrar Desperdício"):
                sel = producao[producao["produto"] == produto].iloc[0]
                try:
                    supabase.table("desperdicio").insert({
                        "data_desperdicio": datetime.now().strftime("%Y-%m-%d"),
                        "produto": produto,
                        "cor": sel["cor"],
                        "quantidade_desperdicada": quantidade,
                        "motivo": motivo,
                        "id_producao": sel["id"],
                        "data_producao": sel["data_producao"]
                    }).execute()
                    st.success("✅ Desperdício registrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao registrar desperdício: {e}")

        st.divider()
        st.subheader("🧾 Desperdícios recentes")
        try:
            dados_desp = supabase.table("desperdicio").select("*").order("id", desc=True).limit(10).execute().data
            df_desp = pd.DataFrame(dados_desp)
            if not df_desp.empty:
                st.dataframe(df_desp)
            else:
                st.info("Nenhum desperdício registrado ainda.")
        except Exception as e:
            st.error(f"Erro ao carregar desperdícios: {e}")

    # ====================================
    # PAINEL DE STATUS
    # ====================================
    elif menu == "📊 Painel de Status":
        st.header("📊 Situação Atual")
        try:
            dados = supabase.table("producao").select("*").execute().data
            producao = pd.DataFrame(dados)
        except Exception as e:
            st.error(f"Erro ao carregar: {e}")
            return

        if producao.empty:
            st.info("Nenhum produto cadastrado.")
        else:
            producao["data_validade"] = pd.to_datetime(producao["data_validade"], errors="coerce")
            hoje = datetime.now().date()
            producao["dias_restantes"] = producao["data_validade"].apply(
                lambda x: (x.date() - hoje).days if pd.notnull(x) else None
            )
            producao["status"] = producao["dias_restantes"].apply(
                lambda d: "✅ Dentro do prazo" if d and d > 2 else ("⚠️ Perto do vencimento" if d and d > 0 else "❌ Vencido")
            )
            st.dataframe(producao[["id","produto","cor","data_producao","data_validade","dias_restantes","status"]])

    # ====================================
    # RELATÓRIOS
    # ====================================
    elif menu == "📈 Relatórios":
        st.header("📈 Relatórios de Produção e Desperdício")
        aba = st.radio("Escolha o tipo:", ["Produção", "Desperdício"])
        if aba == "Produção":
            df = pd.DataFrame(supabase.table("producao").select("*").execute().data)
            if df.empty:
                st.info("Sem produções.")
            else:
                df_resumo = df.groupby("produto")["quantidade_produzida"].sum().reset_index()
                st.bar_chart(df_resumo.set_index("produto"))
                st.dataframe(df_resumo)
        else:
            df = pd.DataFrame(supabase.table("desperdicio").select("*").execute().data)
            if df.empty:
                st.info("Sem desperdícios.")
            else:
                df_resumo = df.groupby("produto")["quantidade_desperdicada"].sum().reset_index()
                st.bar_chart(df_resumo.set_index("produto"))
                st.dataframe(df_resumo)

# ====================================
# EXECUÇÃO
# ====================================
if "logado" not in st.session_state or not st.session_state["logado"]:
    login_page()
else:
    main_app()
