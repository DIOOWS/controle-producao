import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os

# ====================================
# CONFIGURAÇÃO DA PÁGINA
# ====================================
st.set_page_config(page_title="Controle de Produção e Desperdício", page_icon="🏭", layout="wide")

DEBUG_MODE = "streamlit_app_name" in os.environ or st.sidebar.checkbox("🧩 Ativar modo debug (manual)")
if DEBUG_MODE:
    st.sidebar.warning("🧩 Modo Debug Ativo — Logs habilitados.")

# ====================================
# CONEXÃO COM GOOGLE SHEETS
# ====================================
def conectar_sheets():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["connections"]["gsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        planilha = client.open_by_key("1U3XbcY2uGBNrcsQZDAEuo4O-9yH2-FuMUctsb11a69E")
        if DEBUG_MODE:
            st.success("✅ Conectado ao Google Sheets.")
        return planilha
    except Exception as e:
        st.error(f"❌ Erro na conexão: {e}")
        return None

# ====================================
# USUÁRIOS (Login e Cadastro)
# ====================================
def carregar_usuarios(planilha):
    try:
        ws = planilha.worksheet("usuarios")
        usuarios = pd.DataFrame(ws.get_all_records())

        # Garante colunas mesmo se estiverem vazias
        colunas = ["usuario","senha","nome","criado_em"]
        for c in colunas:
            if c not in usuarios.columns:
                usuarios[c] = ""

        # Se estiver vazio, cria usuário padrão
        if usuarios.empty:
            ws.update([colunas, ["admin","1234","Administrador",datetime.now().strftime("%Y-%m-%d %H:%M")]])
            return pd.DataFrame([{
                "usuario":"admin","senha":"1234","nome":"Administrador",
                "criado_em":datetime.now().strftime("%Y-%m-%d %H:%M")
            }])

        return usuarios[colunas]

    except Exception:
        # Se a aba não existir, cria automaticamente
        ws = planilha.add_worksheet(title="usuarios", rows=100, cols=4)
        ws.update([["usuario","senha","nome","criado_em"],
                   ["admin","1234","Administrador",datetime.now().strftime("%Y-%m-%d %H:%M")]])
        return pd.DataFrame([{
            "usuario":"admin","senha":"1234","nome":"Administrador",
            "criado_em":datetime.now().strftime("%Y-%m-%d %H:%M")
        }])

def salvar_usuario(planilha, usuario, senha, nome):
    usuarios = carregar_usuarios(planilha)
    if usuario in usuarios["usuario"].values:
        st.warning("⚠️ Usuário já cadastrado.")
        return

    novo = pd.DataFrame([{
        "usuario": usuario,
        "senha": senha,
        "nome": nome,
        "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M")
    }])
    usuarios = pd.concat([usuarios, novo], ignore_index=True)
    ws = planilha.worksheet("usuarios")
    ws.clear()
    ws.update([usuarios.columns.values.tolist()] + usuarios.values.tolist())
    st.success("✅ Usuário cadastrado com sucesso!")

def autenticar_usuario(planilha, usuario, senha):
    usuarios = carregar_usuarios(planilha)
    match = usuarios[(usuarios["usuario"] == usuario) & (usuarios["senha"] == senha)]
    return not match.empty

# ====================================
# PÁGINA DE LOGIN
# ====================================
def login_page():
    st.title("🔐 Login - Sistema de Controle de Produção")

    tab1, tab2 = st.tabs(["Entrar", "Cadastrar Novo Usuário"])

    with tab1:
        usuario = st.text_input("Usuário")
        senha = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            if autenticar_usuario(planilha, usuario, senha):
                st.session_state["usuario_logado"] = usuario
                st.success(f"Bem-vindo, {usuario}! ✅")
                st.rerun()
            else:
                st.error("❌ Usuário ou senha incorretos.")

    with tab2:
        nome = st.text_input("Nome Completo")
        novo_usuario = st.text_input("Novo Usuário")
        nova_senha = st.text_input("Nova Senha", type="password")
        if st.button("Cadastrar"):
            if not nome or not novo_usuario or not nova_senha:
                st.warning("Preencha todos os campos.")
            else:
                salvar_usuario(planilha, novo_usuario, nova_senha, nome)

# ====================================
# CONECTA À PLANILHA E INICIA LOGIN
# ====================================
planilha = conectar_sheets()
if planilha is None:
    st.stop()

if "usuario_logado" not in st.session_state:
    login_page()
    st.stop()

usuario = st.session_state["usuario_logado"]

# ====================================
# INTERFACE PRINCIPAL APÓS LOGIN
# ====================================
st.sidebar.markdown(f"👤 Usuário: **{usuario}**")
if st.sidebar.button("🚪 Sair"):
    del st.session_state["usuario_logado"]
    st.rerun()

st.title("🏭 Controle de Produção e Desperdício - Painel Principal")
st.success(f"✅ Logado como **{usuario}**")

st.write("Aqui você pode adicionar as seções de Produção, Desperdício e Relatórios da sua versão 1.5+.")
st.info("💡 Tudo o que já existia no sistema anterior continua funcionando — apenas protegemos com login.")

# ====================================
# RODAPÉ
# ====================================
st.markdown("---")
st.caption("📘 Sistema de Controle de Produção e Desperdício - Versão 1.7.1 | Login e Cadastro Integrados | Desenvolvido por Diogo Silva 💼")
