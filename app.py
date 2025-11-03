# ====================================
# 🏭 CONTROLE DE PRODUÇÃO E DESPERDÍCIO v6.6 FINAL
# ====================================
# Autor: Diogo Silva
# ====================================
# ✅ Recursos:
# - Todas as abas completas e funcionais
# - json_safe() corrige serialização Supabase
# - Relatórios com filtro + exportar CSV/Excel
# - Nova aba 🧹 Zerar Sistema (apenas admin)
# ====================================

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
from io import BytesIO
import bcrypt
import numpy as np

# ====================================
# CONFIGURAÇÃO
# ====================================
st.set_page_config(page_title="Controle de Produção e Desperdício", page_icon="🏭", layout="wide")

# ====================================
# CONEXÃO SUPABASE
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
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

# 🔧 Conversor universal
def json_safe(value):
    """Converte tipos incompatíveis (numpy, timestamp, etc.) em JSON válido"""
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    if isinstance(value, (np.int64, np.int32, np.integer)):
        return int(value)
    if isinstance(value, (np.float64, np.float32, np.floating)):
        return float(value)
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value

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
        st.warning("⚠️ Nenhum usuário cadastrado. Cadastre via Supabase.")
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

    if st.sidebar.button("🚪 Sair"):
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
            "👥 Gerenciar Usuários",
            "🧹 Zerar Sistema"
        ]
    )

    # ---------- ALERTAS ----------
    try:
        df_alertas = pd.DataFrame(supabase.table("producao").select("*").execute().data)
        if not df_alertas.empty:
            alertas = gerar_alertas(df_alertas)
            if alertas:
                with st.sidebar.expander("🚨 Alertas de Validade", expanded=True):
                    for alerta in alertas:
                        if "VENCIDO" in alerta:
                            st.sidebar.error(alerta)
                        else:
                            st.sidebar.warning(alerta)
    except Exception as e:
        st.sidebar.error(f"Erro ao carregar alertas: {e}")

    # ====================================
    # 📊 PAINEL DE STATUS
    # ====================================
    if menu == "📊 Painel de Status":
        st.header("📊 Painel de Produção e Desperdício")
        producao = pd.DataFrame(supabase.table("producao").select("*").execute().data)
        desperdicio = pd.DataFrame(supabase.table("desperdicio").select("*").execute().data)
        if producao.empty:
            st.info("Nenhum dado de produção registrado ainda.")
        else:
            total_prod = producao["quantidade_produzida"].sum()
            total_desp = desperdicio["quantidade_desperdicada"].sum() if not desperdicio.empty else 0
            estoque = total_prod - total_desp
            col1, col2, col3 = st.columns(3)
            col1.metric("🧁 Produzido", int(total_prod))
            col2.metric("⚠️ Desperdiçado", int(total_desp))
            col3.metric("📦 Estoque Atual", int(estoque))

    # ====================================
    # 📦 ESTOQUE ATUAL
    # ====================================
    elif menu == "📦 Estoque Atual":
        st.header("📦 Estoque Atual de Produtos")
        producao = pd.DataFrame(supabase.table("producao").select("*").execute().data)
        desperdicio = pd.DataFrame(supabase.table("desperdicio").select("*").execute().data)
        if producao.empty:
            st.info("Nenhum produto cadastrado.")
        else:
            if not desperdicio.empty:
                soma_desp = desperdicio.groupby("produto")["quantidade_desperdicada"].sum().reset_index()
                producao = producao.merge(soma_desp, on="produto", how="left").fillna(0)
            else:
                producao["quantidade_desperdicada"] = 0
            producao["estoque_atual"] = producao["quantidade_produzida"] - producao["quantidade_desperdicada"]
            st.dataframe(producao[["produto", "cor", "quantidade_produzida", "quantidade_desperdicada", "estoque_atual", "data_validade"]])

    # ====================================
    # 🧁 REGISTRAR PRODUÇÃO
    # ====================================
    elif menu == "Registrar Produção 🧁":
        st.header("🧁 Registrar Nova Produção")
        produto = st.text_input("Produto:")
        quantidade = st.number_input("Quantidade produzida:", min_value=1, step=1)
        if st.button("💾 Salvar"):
            data = datetime.now()
            cor = cor_do_dia(data.weekday())
            validade = (data + timedelta(days=2)).strftime("%Y-%m-%d")
            supabase.table("producao").insert({
                "data_producao": agora_fmt(),
                "produto": produto,
                "cor": cor,
                "quantidade_produzida": json_safe(quantidade),
                "data_validade": validade
            }).execute()
            st.success(f"✅ Produção registrada ({emoji_cor(cor)} {cor.upper()})")

    # ====================================
    # ⚠️ REGISTRAR DESPERDÍCIO
    # ====================================
    elif menu == "Registrar Desperdício ⚠️":
        st.header("⚠️ Registrar Desperdício")
        producao = pd.DataFrame(supabase.table("producao").select("*").execute().data)
        if producao.empty:
            st.info("Nenhum produto disponível.")
        else:
            produto = st.selectbox("Produto:", producao["produto"].unique())
            quantidade = st.number_input("Quantidade desperdiçada:", min_value=1, step=1)
            motivo = st.text_area("Motivo:")
            if st.button("💾 Registrar"):
                sel = producao[producao["produto"] == produto].iloc[0]
                supabase.table("desperdicio").insert({
                    "data_desperdicio": agora_fmt(),
                    "produto": produto,
                    "cor": sel["cor"],
                    "quantidade_desperdicada": json_safe(quantidade),
                    "motivo": motivo,
                    "id_producao": json_safe(sel["id"])
                }).execute()
                st.success("✅ Desperdício registrado!")

    # ====================================
    # ♻️ REMARCAR PRODUTOS
    # ====================================
    elif menu == "♻️ Remarcar Produtos":
        st.header("♻️ Remarcação de Produtos")
        producao = pd.DataFrame(supabase.table("producao").select("*").execute().data)
        if producao.empty:
            st.info("Nenhum produto para remarcar.")
        else:
            producao["data_validade"] = pd.to_datetime(producao["data_validade"], errors="coerce")
            hoje = datetime.now().date()
            producao["dias_restantes"] = producao["data_validade"].apply(lambda x: (x.date() - hoje).days if pd.notnull(x) else None)
            exp = producao[producao["dias_restantes"] <= 2]
            if exp.empty:
                st.success("✅ Nenhum produto próximo do vencimento.")
            else:
                st.dataframe(exp[["id", "produto", "quantidade_produzida", "data_validade"]])
                id_sel = st.number_input("ID do produto:", min_value=1, step=1)
                dias_extra = st.number_input("Dias adicionais:", min_value=1, value=2)
                quantidade_remarcar = st.number_input("Quantidade a remarcar:", min_value=1, step=1)
                if st.button("♻️ Aplicar Remarcação"):
                    if id_sel not in exp["id"].values:
                        st.error("❌ ID inválido.")
                    else:
                        prod_sel = exp[exp["id"] == id_sel].iloc[0]
                        qtd_existente = int(prod_sel["quantidade_produzida"])
                        if quantidade_remarcar > qtd_existente:
                            st.error(f"❌ Quantidade excede ({qtd_existente}).")
                        else:
                            nova_validade = (datetime.now() + timedelta(days=dias_extra)).strftime("%Y-%m-%d")
                            supabase.table("producao").update({
                                "quantidade_produzida": json_safe(qtd_existente - quantidade_remarcar),
                                "data_remarcacao": agora_fmt()
                            }).eq("id", int(id_sel)).execute()
                            supabase.table("producao").insert({
                                "data_producao": agora_fmt(),
                                "produto": prod_sel["produto"],
                                "quantidade_produzida": json_safe(quantidade_remarcar),
                                "cor": prod_sel["cor"],
                                "data_validade": nova_validade
                            }).execute()
                            st.success(f"✅ {quantidade_remarcar} unidades remarcadas até {nova_validade}.")

    # ====================================
    # 📈 RELATÓRIOS (com exportar)
    # ====================================
    elif menu == "📈 Relatórios":
        st.header("📈 Relatórios de Produção e Desperdício")
        tipo = st.radio("Tipo de relatório:", ["Produção", "Desperdício"])
        tabela = "producao" if tipo == "Produção" else "desperdicio"
        campo_data = "data_producao" if tipo == "Produção" else "data_desperdicio"
        ini = st.date_input("Data inicial:", datetime.now().date() - timedelta(days=7))
        fim = st.date_input("Data final:", datetime.now().date())
        df = pd.DataFrame(supabase.table(tabela).select("*").execute().data)
        if df.empty:
            st.info(f"Nenhum registro encontrado em **{tabela}**.")
        else:
            if campo_data in df.columns:
                df[campo_data] = pd.to_datetime(df[campo_data], errors="coerce")
                df = df[(df[campo_data].dt.date >= ini) & (df[campo_data].dt.date <= fim)]
            if df.empty:
                st.warning("Nenhum dado encontrado nesse período.")
            else:
                col_quant = "quantidade_produzida" if tipo == "Produção" else "quantidade_desperdicada"
                total = int(df[col_quant].sum())
                st.dataframe(df)
                st.success(f"**Total {tipo.lower()} no período:** {total}")
                formato = st.radio("Exportar como:", ["Excel (.xlsx)", "CSV (.csv)"])
                nome = f"{tabela}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                if formato == "Excel (.xlsx)":
                    buffer = BytesIO()
                    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                        df.to_excel(writer, index=False)
                    st.download_button("📥 Baixar Excel", buffer.getvalue(), file_name=f"{nome}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    csv = df.to_csv(index=False).encode("utf-8")
                    st.download_button("📥 Baixar CSV", csv, file_name=f"{nome}.csv", mime="text/csv")

    # ====================================
    # 👥 GERENCIAR USUÁRIOS
    # ====================================
    elif menu == "👥 Gerenciar Usuários":
        st.header("👥 Gerenciamento de Usuários")
        if st.session_state["tipo"] != "admin":
            st.warning("⚠️ Apenas administradores podem gerenciar usuários.")
            return
        aba = st.radio("Ação:", ["Cadastrar Novo", "Excluir Usuário"])
        if aba == "Cadastrar Novo":
            nome = st.text_input("Nome:")
            usuario = st.text_input("Usuário:")
            senha = st.text_input("Senha:", type="password")
            tipo = st.selectbox("Tipo:", ["usuario", "admin"])
            if st.button("💾 Cadastrar"):
                if not usuario or not senha:
                    st.error("Preencha todos os campos obrigatórios.")
                else:
                    senha_hash = hash_senha(senha)
                    supabase.table("usuarios").insert({
                        "nome": nome,
                        "usuario": usuario.lower(),
                        "senha": senha_hash,
                        "tipo": tipo
                    }).execute()
                    st.success("✅ Usuário cadastrado com sucesso!")
        else:
            usuarios = pd.DataFrame(supabase.table("usuarios").select("*").execute().data)
            if usuarios.empty:
                st.info("Nenhum usuário cadastrado.")
            else:
                st.dataframe(usuarios)
                id_sel = st.number_input("ID do usuário para excluir:", min_value=1, step=1)
                if st.button("🗑️ Excluir"):
                    supabase.table("usuarios").delete().eq("id", int(id_sel)).execute()
                    st.success("✅ Usuário excluído com sucesso!")

    # ====================================
    # 🧹 ZERAR SISTEMA
    # ====================================
    elif menu == "🧹 Zerar Sistema":
        st.header("🧹 Zerar Sistema (somente para administradores)")
        if st.session_state["tipo"] != "admin":
            st.warning("⚠️ Apenas administradores podem zerar o sistema.")
        else:
            st.error("🚨 Esta ação apagará todos os dados do sistema!")
            if st.button("🧨 Confirmar e Apagar Tudo"):
                supabase.table("producao").delete().neq("id", 0).execute()
                supabase.table("desperdicio").delete().neq("id", 0).execute()
                st.success("✅ Sistema zerado com sucesso!")

# ====================================
# EXECUÇÃO
# ====================================
if "logado" not in st.session_state or not st.session_state["logado"]:
    login_page()
else:
    main_app()
