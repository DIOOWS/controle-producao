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
    mapa = {
        "azul": "🟦", "verde": "🟩", "amarelo": "🟨", "laranja": "🟧",
        "vermelho": "🟥", "prata": "⬜", "dourado": "🟨✨"
    }
    return mapa.get(cor, "⬛")

def hash_senha(senha):
    return bcrypt.hashpw(senha.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

def verificar_senha(senha_digitada, senha_hash):
    try:
        return bcrypt.checkpw(senha_digitada.encode("utf-8"), senha_hash.encode("utf-8"))
    except Exception:
        return False

def gerar_alertas(df):
    hoje = datetime.now().date()
    df["data_validade"] = pd.to_datetime(df["data_validade"], errors="coerce")
    df["dias"] = df["data_validade"].apply(lambda x: (x.date() - hoje).days if pd.notnull(x) else None)

    vencendo = df[df["dias"].between(0, 2, inclusive="both")]
    vencidos = df[df["dias"] < 0]

    alertas = []
    for _, row in vencendo.iterrows():
        alertas.append(f"⚠️ {row['produto']} ({row['cor']}) vence em {row['dias']} dia(s)")
    for _, row in vencidos.iterrows():
        alertas.append(f"❌ {row['produto']} ({row['cor']}) VENCIDO!")
    return alertas

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
    # ALERTAS (sidebar + popup)
    # ====================================
    try:
        dados_alertas = supabase.table("producao").select("*").execute().data
        df_alertas = pd.DataFrame(dados_alertas)
        if not df_alertas.empty:
            alertas = gerar_alertas(df_alertas)
            for a in alertas:
                if "VENCIDO" in a:
                    st.sidebar.error(a)
                else:
                    st.sidebar.warning(a)
            # popup central
            if alertas:
                with st.expander("🚨 Produtos com alerta de validade:"):
                    for a in alertas:
                        st.write(a)
        else:
            st.sidebar.info("Nenhum produto cadastrado.")
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar alertas: {e}")

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

    # ====================================
    # REGISTRAR DESPERDÍCIO
    # ====================================
    elif menu == "Registrar Desperdício ⚠️":
        st.header("⚠️ Registrar Desperdício")
        dados = supabase.table("producao").select("*").execute().data
        producao = pd.DataFrame(dados)
        if producao.empty:
            st.info("Nenhum produto cadastrado.")
        else:
            produto = st.selectbox("Selecione o produto:", producao["produto"].unique())
            quantidade = st.number_input("Quantidade desperdiçada:", min_value=1, step=1)
            motivo = st.text_area("Motivo do desperdício:")

            if st.button("💾 Registrar Desperdício"):
                sel = producao[producao["produto"] == produto].iloc[0]
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

    # ====================================
    # REMARCAR PRODUTOS
    # ====================================
    elif menu == "♻️ Remarcar Produtos":
        st.header("♻️ Remarcação de Produtos")
        producao = pd.DataFrame(supabase.table("producao").select("*").execute().data)
        if producao.empty:
            st.info("Nenhum produto cadastrado.")
        else:
            producao["data_validade"] = pd.to_datetime(producao["data_validade"], errors="coerce")
            hoje = datetime.now().date()
            producao["dias_restantes"] = producao["data_validade"].apply(
                lambda x: (x.date() - hoje).days if pd.notnull(x) else None
            )
            exp = producao[producao["dias_restantes"] <= 2]
            if exp.empty:
                st.success("✅ Nenhum produto perto do vencimento.")
            else:
                st.dataframe(exp)
                id_sel = st.number_input("ID do produto para remarcar:", min_value=1, step=1)
                dias_extra = st.number_input("Dias adicionais de validade:", min_value=1, value=2)
                if st.button("♻️ Aplicar Remarcação"):
                    nova_validade = (datetime.now() + timedelta(days=dias_extra)).strftime("%Y-%m-%d")
                    supabase.table("producao").update({
                        "data_remarcacao": datetime.now().strftime("%Y-%m-%d"),
                        "data_validade": nova_validade
                    }).eq("id", int(id_sel)).execute()
                    st.success(f"✅ Produto ID {id_sel} remarcado até {nova_validade}.")

    # ====================================
    # RELATÓRIOS
    # ====================================
    elif menu == "📈 Relatórios":
        st.header("📈 Relatórios de Produção e Desperdício")
        aba = st.radio("Escolha o tipo de relatório:", ["Produção", "Desperdício"])
        col1, col2 = st.columns(2)
        with col1:
            data_inicio = st.date_input("Data inicial", datetime.now().date() - timedelta(days=7))
        with col2:
            data_fim = st.date_input("Data final", datetime.now().date())

        if aba == "Produção":
            df = pd.DataFrame(supabase.table("producao").select("*").execute().data)
            if df.empty:
                st.info("Nenhuma produção registrada.")
            else:
                df["data_producao"] = pd.to_datetime(df["data_producao"], errors="coerce")
                df = df[(df["data_producao"].dt.date >= data_inicio) & (df["data_producao"].dt.date <= data_fim)]
                df_sum = df.groupby("produto")["quantidade_produzida"].sum().reset_index()
                st.bar_chart(df_sum.set_index("produto"))
                st.dataframe(df_sum)
        else:
            df = pd.DataFrame(supabase.table("desperdicio").select("*").execute().data)
            if df.empty:
                st.info("Nenhum desperdício registrado.")
            else:
                df["data_desperdicio"] = pd.to_datetime(df["data_desperdicio"], errors="coerce")
                df = df[(df["data_desperdicio"].dt.date >= data_inicio) & (df["data_desperdicio"].dt.date <= data_fim)]
                df_sum = df.groupby("produto")["quantidade_desperdicada"].sum().reset_index()
                st.bar_chart(df_sum.set_index("produto"))
                st.dataframe(df_sum)

    # ====================================
    # EXPORTAR
    # ====================================
    elif menu == "📤 Exportar":
        st.header("📤 Exportar Dados Filtrados")
        aba = st.radio("Escolha o tipo:", ["Produção", "Desperdício"])
        formato = st.radio("Formato:", ["Excel (.xlsx)", "CSV (.csv)"])
        df = pd.DataFrame(supabase.table("producao" if aba == "Produção" else "desperdicio").select("*").execute().data)
        if df.empty:
            st.warning("⚠️ Nenhum dado encontrado.")
        else:
            if formato == "Excel (.xlsx)":
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    df.to_excel(writer, index=False, sheet_name=aba)
                st.download_button("📥 Baixar Excel", data=buffer.getvalue(), file_name=f"{aba.lower()}.xlsx",
                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            else:
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button("📥 Baixar CSV", data=csv, file_name=f"{aba.lower()}.csv", mime="text/csv")

    # ====================================
    # GERENCIAR USUÁRIOS
    # ====================================
    elif menu == "👥 Gerenciar Usuários":
        st.header("👥 Gerenciamento de Usuários")
        if st.session_state["tipo"] != "admin":
            st.warning("⚠️ Apenas o ADMIN pode gerenciar usuários.")
        else:
            aba = st.radio("Ação:", ["Cadastrar Novo", "Editar / Excluir"])
            if aba == "Cadastrar Novo":
                nome = st.text_input("Nome:")
                usuario = st.text_input("Usuário:")
                senha = st.text_input("Senha:", type="password")
                tipo = st.selectbox("Tipo:", ["usuario", "admin"])
                if st.button("💾 Cadastrar"):
                    senha_hash = hash_senha(senha)
                    supabase.table("usuarios").insert({
                        "nome": nome,
                        "usuario": usuario,
                        "senha": senha_hash,
                        "tipo": tipo
                    }).execute()
                    st.success("✅ Usuário cadastrado com sucesso!")
            else:
                usuarios = pd.DataFrame(supabase.table("usuarios").select("*").execute().data)
                st.dataframe(usuarios)
                id_sel = st.number_input("ID do usuário:", min_value=1, step=1)
                nova_senha = st.text_input("Nova senha (opcional):", type="password")
                novo_tipo = st.selectbox("Novo tipo:", ["usuario", "admin"])
                if st.button("✏️ Atualizar"):
                    update = {"tipo": novo_tipo}
                    if nova_senha:
                        update["senha"] = hash_senha(nova_senha)
                    supabase.table("usuarios").update(update).eq("id", int(id_sel)).execute()
                    st.success("✅ Usuário atualizado!")
                if st.button("🗑️ Excluir"):
                    supabase.table("usuarios").delete().eq("id", int(id_sel)).execute()
                    st.warning("🗑️ Usuário excluído!")

    # ====================================
    # ZERAR SISTEMA
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
