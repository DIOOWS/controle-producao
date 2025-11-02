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
    # PAINEL DE STATUS
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
            # 🔹 Converte a coluna de validade para datetime corretamente
            producao["data_validade"] = pd.to_datetime(producao["data_validade"], errors="coerce")
            producao["data_producao"] = pd.to_datetime(producao["data_producao"], errors="coerce")

            hoje = datetime.now().date()

            # 🔹 Calcula dias restantes com segurança
            producao["dias_restantes"] = producao["data_validade"].apply(
                lambda x: (x.date() - hoje).days if pd.notnull(x) else None
            )

            # 🔹 Define o status conforme a validade
            def status_vencimento(dias):
                if dias is None:
                    return "❓ Sem data"
                elif dias > 2:
                    return "✅ Dentro do prazo"
                elif 0 < dias <= 2:
                    return "⚠️ Perto do vencimento"
                else:
                    return "❌ Vencido"

            producao["status"] = producao["dias_restantes"].apply(status_vencimento)

            # 🔹 Mostra tabela detalhada
            st.dataframe(
                producao[["id", "produto", "cor", "data_producao", "data_validade", "dias_restantes", "status"]]
            )

            # 🔹 Mostra métricas no topo
            col1, col2, col3 = st.columns(3)
            total = len(producao)
            vencidos = len(producao[producao["status"].str.contains("Vencido")])
            perto = len(producao[producao["status"].str.contains("Perto")])
            ativos = total - vencidos - perto

            col1.metric("🧁 Total de Produtos", total)
            col2.metric("⚠️ Perto do Vencimento", perto)
            col3.metric("❌ Vencidos", vencidos)

    # ====================================
    # EXPORTAR RELATÓRIOS / DADOS
    # ====================================
    elif menu == "📤 Exportar":
        st.header("📤 Exportar Dados do Sistema")

        # Opções de exportação
        aba = st.radio("Escolha o tipo de dado para exportar:", ["Produção", "Desperdício"])
        formato = st.radio("Formato do arquivo:", ["Excel (.xlsx)", "CSV (.csv)"])

        # Mapeia o nome da aba para o nome da tabela correta no Supabase
        tabela = "producao" if aba == "Produção" else "desperdicio"

        try:
            # Busca os dados diretamente do Supabase
            dados = supabase.table(tabela).select("*").execute().data
            df = pd.DataFrame(dados)
        except Exception as e:
            st.error(f"❌ Erro ao buscar dados: {e}")
            st.stop()

        if df.empty:
            st.warning(f"⚠️ Nenhum dado encontrado na tabela '{tabela}'.")
        else:
            st.success(f"✅ {len(df)} registros carregados da tabela '{tabela}'.")

            nome_arquivo = f"{tabela}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Exportar como Excel
            if formato == "Excel (.xlsx)":
                from io import BytesIO
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    df.to_excel(writer, index=False, sheet_name=tabela.capitalize())
                st.download_button(
                    label="📥 Baixar Excel",
                    data=buffer.getvalue(),
                    file_name=f"{nome_arquivo}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            # Exportar como CSV
            else:
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Baixar CSV",
                    data=csv,
                    file_name=f"{nome_arquivo}.csv",
                    mime="text/csv"
                )


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
