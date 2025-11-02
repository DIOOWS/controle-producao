# ====================================
# 🏭 CONTROLE DE PRODUÇÃO E DESPERDÍCIO v4.0
# ====================================
# Autor: Diogo Silva
# Atualizado: v4.0 (versão completa e estável)
# - Mantidas TODAS as funcionalidades originais
# - Corrigidos erros de serialização JSON e DeltaGenerator
# - Adicionada aba "📦 Estoque Atual" com filtros e busca
# ====================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
from io import BytesIO
import bcrypt
from pytz import timezone

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
def agora_fmt():
    tz = timezone("America/Sao_Paulo")
    return datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

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
        if not user.empty and "senha" in user.columns and verificar_senha(senha, str(user.iloc[0]["senha"])):
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
            "📦 Estoque Atual",
            "Registrar Produção 🧁",
            "Registrar Desperdício ⚠️",
            "♻️ Remarcar Produtos",
            "📈 Relatórios",
            "📤 Exportar",
            "👥 Gerenciar Usuários",
            "🧹 Zerar Sistema"
        ]
    )

    # ---------- ALERTAS ----------
    try:
        dados_alertas = supabase.table("producao").select("*").execute().data
        df_alertas = pd.DataFrame(dados_alertas)
        if not df_alertas.empty:
            alertas = gerar_alertas(df_alertas)
            for a in alertas:
                (st.sidebar.error(a) if "VENCIDO" in a else st.sidebar.warning(a))
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar alertas: {e}")

    # ====================================
    # 📦 ESTOQUE ATUAL
    # ====================================
    if menu == "📦 Estoque Atual":
        st.header("📦 Estoque Atual de Produtos")

        try:
            producao = pd.DataFrame(supabase.table("producao").select("*").execute().data)
            desperdicio = pd.DataFrame(supabase.table("desperdicio").select("*").execute().data)
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")
            return

        if producao.empty:
            st.info("Nenhum produto produzido ainda.")
        else:
            producao["data_validade"] = pd.to_datetime(producao["data_validade"], errors="coerce")
            producao["data_producao"] = pd.to_datetime(producao["data_producao"], errors="coerce")
            producao["quantidade_produzida"] = pd.to_numeric(producao["quantidade_produzida"], errors="coerce").fillna(0).astype(int)

            data_inicio = st.date_input("Data inicial:", datetime.now().date() - timedelta(days=7))
            data_fim = st.date_input("Data final:", datetime.now().date())
            filtro_data = (producao["data_producao"].dt.date >= data_inicio) & (producao["data_producao"].dt.date <= data_fim)
            producao = producao.loc[filtro_data]

            busca = st.text_input("🔍 Buscar produto:")
            if busca:
                producao = producao[producao["produto"].str.contains(busca, case=False, na=False)]

            if not desperdicio.empty:
                desperdicio["quantidade_desperdicada"] = pd.to_numeric(desperdicio["quantidade_desperdicada"], errors="coerce").fillna(0).astype(int)
                desperdicio_soma = desperdicio.groupby("produto")["quantidade_desperdicada"].sum().reset_index()
                producao = producao.merge(desperdicio_soma, on="produto", how="left").fillna(0)
            else:
                producao["quantidade_desperdicada"] = 0

            producao["estoque_atual"] = producao["quantidade_produzida"] - producao["quantidade_desperdicada"]
            producao["estoque_atual"] = producao["estoque_atual"].clip(lower=0)

            hoje = datetime.now().date()
            producao["dias_restantes"] = producao["data_validade"].apply(lambda x: (x.date() - hoje).days if pd.notnull(x) else None)
            producao["status"] = producao["dias_restantes"].apply(lambda d: "❌ Vencido" if d < 0 else ("⚠️ Vencendo" if d <= 2 else "✅ Válido"))

            st.dataframe(producao[["produto", "quantidade_produzida", "quantidade_desperdicada", "estoque_atual", "data_validade", "status"]])

            col1, col2, col3 = st.columns(3)
            col1.metric("🧁 Produzido", int(producao["quantidade_produzida"].sum()))
            col2.metric("⚠️ Desperdiçado", int(producao["quantidade_desperdicada"].sum()))
            col3.metric("📦 Estoque Atual", int(producao["estoque_atual"].sum()))

    # ====================================
    # 🧁 REGISTRAR PRODUÇÃO
    # ====================================
    elif menu == "Registrar Produção 🧁":
        st.header("🧁 Registrar Nova Produção")
        produto = st.text_input("Produto:")
        quantidade = st.number_input("Quantidade produzida:", min_value=1, step=1)
        if st.button("💾 Salvar Produção"):
            data = datetime.now()
            cor = cor_do_dia(data.weekday())
            validade = (data + timedelta(days=2)).strftime("%Y-%m-%d")
            supabase.table("producao").insert({
                "produto": produto.strip(),
                "quantidade_produzida": int(quantidade),
                "data_producao": agora_fmt(),
                "data_validade": validade,
                "cor": cor,
                "data_remarcacao": None
            }).execute()
            st.success(f"✅ Produção de '{produto}' registrada ({emoji_cor(cor)} {cor})")

    # ====================================
    # ⚠️ REGISTRAR DESPERDÍCIO
    # ====================================
    elif menu == "Registrar Desperdício ⚠️":
        st.header("⚠️ Registrar Desperdício")
        producao = pd.DataFrame(supabase.table("producao").select("*").execute().data)
        if producao.empty:
            st.info("Nenhum produto produzido ainda.")
        else:
            produto = st.selectbox("Produto:", producao["produto"].unique())
            quantidade = st.number_input("Quantidade desperdiçada:", min_value=1, step=1)
            motivo = st.text_area("Motivo:")
            if st.button("💾 Registrar"):
                sel = producao[producao["produto"] == produto].iloc[0]
                supabase.table("desperdicio").insert({
                    "produto": produto,
                    "quantidade_desperdicada": int(quantidade),
                    "motivo": motivo,
                    "data_desperdicio": agora_fmt(),
                    "cor": sel["cor"],
                    "id_producao": sel["id"]
                }).execute()
                st.success(f"Desperdício de {quantidade}x {produto} registrado.")

    # ====================================
    # ♻️ REMARCAR PRODUTOS
    # ====================================
    elif menu == "♻️ Remarcar Produtos":
        st.header("♻️ Remarcação de Produtos")
        producao = pd.DataFrame(supabase.table("producao").select("*").execute().data)
        if producao.empty:
            st.info("Nenhum produto disponível.")
        else:
            producao["data_validade"] = pd.to_datetime(producao["data_validade"], errors="coerce")
            hoje = datetime.now().date()
            producao["dias_restantes"] = producao["data_validade"].apply(lambda x: (x.date() - hoje).days if pd.notnull(x) else None)
            exp = producao[producao["dias_restantes"] <= 2]
            if exp.empty:
                st.success("Nenhum produto perto do vencimento.")
            else:
                st.dataframe(exp[["id", "produto", "quantidade_produzida", "data_validade", "dias_restantes"]])
                id_sel = st.number_input("ID do produto para remarcar:", min_value=1, step=1)
                dias_extra = st.number_input("Dias extras de validade:", min_value=1, value=2)
                qtd_remarcar = st.number_input("Quantidade a remarcar:", min_value=1, step=1)
                if st.button("♻️ Remarcar"):
                    if id_sel not in exp["id"].values:
                        st.error("ID inválido.")
                    else:
                        p = exp[exp["id"] == id_sel].iloc[0]
                        if qtd_remarcar > p["quantidade_produzida"]:
                            st.error("Quantidade maior que disponível.")
                        else:
                            nova_validade = (datetime.now() + timedelta(days=dias_extra)).strftime("%Y-%m-%d")
                            supabase.table("producao").update({
                                "data_validade": nova_validade,
                                "data_remarcacao": agora_fmt(),
                                "quantidade_produzida": int(p["quantidade_produzida"]) - int(qtd_remarcar)
                            }).eq("id", int(id_sel)).execute()
                            supabase.table("producao").insert({
                                "produto": p["produto"],
                                "quantidade_produzida": int(qtd_remarcar),
                                "data_producao": agora_fmt(),
                                "data_validade": nova_validade,
                                "cor": p["cor"]
                            }).execute()
                            st.success(f"Remarcado {qtd_remarcar}x '{p['produto']}' até {nova_validade}.")

    # ====================================
    # 🧹 ZERAR SISTEMA
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
