import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# ==============================
# CONFIGURAÇÃO
# ==============================
st.set_page_config(page_title="Controle de Produção e Desperdício", page_icon="🏭", layout="wide")
st.title("🏭 Controle de Produção e Desperdício (modo diagnóstico)")
st.markdown("---")

# ==============================
# FUNÇÕES DE CONEXÃO
# ==============================
def conectar_sheets():
    st.info("🔄 Tentando conectar ao Google Sheets...")

    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = st.secrets["connections"]["gsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        st.success("✅ Conexão com Google Sheets estabelecida.")
        planilha = client.open_by_key("1U3XbcY2uGBNrcsQZDAEuo4O-9yH2-FuMUctsb11a69E")
        st.success("✅ Planilha aberta com sucesso!")
        return planilha
    except Exception as e:
        st.error(f"❌ Falha ao conectar ao Google Sheets: {e}")
        return None

def carregar_planilhas(planilha):
    st.info("📂 Carregando abas de produção e desperdício...")
    try:
        producao_ws = planilha.worksheet("producao")
        desperdicio_ws = planilha.worksheet("desperdicio")

        producao = pd.DataFrame(producao_ws.get_all_records())
        desperdicio = pd.DataFrame(desperdicio_ws.get_all_records())

        st.success(f"📊 Produção: {len(producao)} linhas | Desperdício: {len(desperdicio)} linhas")

        if producao.empty:
            producao = pd.DataFrame(columns=[
                "id","data_producao","produto","cor",
                "quantidade_produzida","data_remarcacao","data_validade"
            ])
        if desperdicio.empty:
            desperdicio = pd.DataFrame(columns=[
                "id","data_desperdicio","produto","cor",
                "quantidade_desperdicada","motivo","id_producao","data_producao"
            ])
        return producao, desperdicio
    except Exception as e:
        st.error(f"❌ Erro ao carregar abas: {e}")
        return pd.DataFrame(), pd.DataFrame()

def salvar_planilha(planilha, aba, df):
    try:
        ws = planilha.worksheet(aba)
        ws.clear()
        if not df.empty:
            ws.update([df.columns.values.tolist()] + df.values.tolist())
            st.success(f"✅ Dados salvos na aba '{aba}' ({len(df)} registros).")
        else:
            ws.update([[""]])
            st.warning(f"⚠️ Aba '{aba}' foi limpa (sem dados).")
    except Exception as e:
        st.error(f"❌ Erro ao salvar na aba {aba}: {e}")

# ==============================
# TESTE INICIAL DE CONEXÃO
# ==============================
planilha = conectar_sheets()

if planilha:
    producao, desperdicio = carregar_planilhas(planilha)
else:
    st.stop()

# ==============================
# FUNÇÕES AUXILIARES
# ==============================
def cor_do_dia(dia_semana):
    cores = ["azul","verde","amarelo","laranja","vermelho","prata","dourado"]
    return cores[dia_semana]

def emoji_cor(cor):
    mapa = {
        "azul": "🟦", "verde": "🟩", "amarelo": "🟨",
        "laranja": "🟧", "vermelho": "🟥", "prata": "⬜", "dourado": "🟨✨"
    }
    return mapa.get(cor, "⬛")

# ==============================
# DIAGNÓSTICO DE DADOS
# ==============================
st.subheader("📋 Diagnóstico de Dados Carregados")

col1, col2 = st.columns(2)
with col1:
    st.markdown("### Produção")
    st.dataframe(producao)
with col2:
    st.markdown("### Desperdício")
    st.dataframe(desperdicio)

st.markdown("---")
st.caption("🔍 Modo de diagnóstico: mostra logs de conexão e leitura de planilhas.")
