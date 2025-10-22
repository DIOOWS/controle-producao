import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
import os

# ====================================
# CONFIGURAÇÃO DA PÁGINA
# ====================================
st.set_page_config(page_title="Controle de Produção e Desperdício", page_icon="🏭", layout="wide")


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
        return planilha
    except Exception as e:
        st.error(f"❌ Erro na conexão com Google Sheets: {e}")
        return None


planilha = conectar_sheets()
if planilha is None:
    st.stop()


# ====================================
# GESTÃO DE USUÁRIOS
# ====================================
def carregar_usuarios(planilha):
    try:
        ws = planilha.worksheet("usuarios")
        usuarios = pd.DataFrame(ws.get_all_records())
        return usuarios
    except Exception:
        ws = planilha.add_worksheet(title="usuarios", rows=100, cols=4)
        ws.update([["usuario", "senha", "nome", "criado_em"]])
        return pd.DataFrame(columns=["usuario", "senha", "nome", "criado_em"])


def salvar_usuario(planilha, usuario, senha, nome):
    ws = planilha.worksheet("usuarios")
    usuarios = carregar_usuarios(planilha)
    if usuario in usuarios["usuario"].values:
        st.error("❌ Este usuário já existe!")
        return False
    novo = pd.DataFrame([{
        "usuario": usuario,
        "senha": senha,
        "nome": nome,
        "criado_em": datetime.now().strftime("%Y-%m-%d %H:%M")
    }])
    usuarios = pd.concat([usuarios, novo], ignore_index=True)
    ws.update([usuarios.columns.values.tolist()] + usuarios.values.tolist())
    st.success("✅ Usuário cadastrado com sucesso! Faça login para continuar.")
    return True


# ====================================
# LOGIN E CADASTRO
# ====================================
def login_page():
    st.title("🔐 Login - Controle de Produção e Desperdício")

    aba = st.radio("Escolha uma opção:", ["Entrar", "Cadastrar novo usuário"])

    if aba == "Entrar":
        usuario = st.text_input("Usuário:")
        senha = st.text_input("Senha:", type="password")

        if st.button("Entrar"):
            usuarios = carregar_usuarios(planilha)
            if usuario in usuarios["usuario"].values:
                linha = usuarios[usuarios["usuario"] == usuario].iloc[0]
                if senha == str(linha["senha"]):
                    st.session_state["autenticado"] = True
                    st.session_state["usuario"] = usuario
                    st.session_state["nome"] = linha["nome"]
                    st.success("✅ Login realizado com sucesso!")
                    st.experimental_rerun()
                else:
                    st.error("❌ Senha incorreta.")
            else:
                st.error("❌ Usuário não encontrado.")

    elif aba == "Cadastrar novo usuário":
        nome = st.text_input("Nome completo:")
        usuario = st.text_input("Novo usuário:")
        senha = st.text_input("Senha:", type="password")
        confirmar = st.text_input("Confirmar senha:", type="password")

        if st.button("Cadastrar"):
            if senha != confirmar:
                st.error("❌ As senhas não coincidem.")
            elif usuario.strip() == "" or nome.strip() == "":
                st.error("❌ Preencha todos os campos.")
            else:
                salvar_usuario(planilha, usuario, senha, nome)


# ====================================
# SE NÃO LOGADO, MOSTRAR LOGIN
# ====================================
if "autenticado" not in st.session_state or not st.session_state["autenticado"]:
    login_page()
    st.stop()


# ====================================
# DEMAIS FUNÇÕES DO SISTEMA
# ====================================
def carregar_planilhas(planilha):
    try:
        producao = pd.DataFrame(planilha.worksheet("producao").get_all_records())
        desperdicio = pd.DataFrame(planilha.worksheet("desperdicio").get_all_records())
        if producao.empty:
            producao = pd.DataFrame(
                columns=["id", "data_producao", "produto", "cor", "quantidade_produzida", "data_remarcacao",
                         "data_validade"])
        if desperdicio.empty:
            desperdicio = pd.DataFrame(
                columns=["id", "data_desperdicio", "produto", "cor", "quantidade_desperdicada", "motivo", "id_producao",
                         "data_producao"])
        return producao, desperdicio
    except Exception as e:
        st.error(f"❌ Erro ao carregar planilhas: {e}")
        return pd.DataFrame(), pd.DataFrame()


def salvar_planilha(planilha, aba, df):
    ws = planilha.worksheet(aba)
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.values.tolist())


def cor_do_dia(dia_semana):
    return ["azul", "verde", "amarelo", "laranja", "vermelho", "prata", "dourado"][dia_semana]


def dia_da_cor(cor):
    mapa = {
        "azul": "segunda-feira",
        "verde": "terça-feira",
        "amarelo": "quarta-feira",
        "laranja": "quinta-feira",
        "vermelho": "sexta-feira",
        "prata": "sábado",
        "dourado": "domingo"
    }
    return mapa.get(cor.lower(), "Desconhecido")


def emoji_cor(cor):
    mapa = {"azul": "🟦", "verde": "🟩", "amarelo": "🟨", "laranja": "🟧", "vermelho": "🟥", "prata": "⬜", "dourado": "🟨✨"}
    return mapa.get(cor, "⬛")


# ====================================
# INICIALIZAÇÃO
# ====================================
producao, desperdicio = carregar_planilhas(planilha)

# ====================================
# MENU PRINCIPAL
# ====================================
st.sidebar.success(f"👋 Olá, {st.session_state['nome']}!")
menu = st.sidebar.radio(
    "Menu principal:",
    ["📊 Painel de Status", "Registrar Produção 🧁", "Registrar Desperdício ⚠️", "Relatórios 📈", "Sair 🚪"]
)

if menu == "Sair 🚪":
    st.session_state.clear()
    st.success("Você saiu do sistema.")
    st.experimental_rerun()

# ====================================
# RESTANTE DAS FUNCIONALIDADES
# ====================================
# (mesmo código anterior para registrar produção, desperdício, relatórios etc.)
st.markdown("---")
st.caption("📘 Sistema de Controle de Produção e Desperdício - Versão 1.7 | Desenvolvido por Diogo Silva 💼")
