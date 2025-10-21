import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials

# ====================================
# CONFIGURAÇÃO DA PÁGINA
# ====================================
st.set_page_config(page_title="Controle de Produção e Desperdício", page_icon="🏭", layout="wide")

# ====================================
# CONEXÃO COM GOOGLE SHEETS
# ====================================
def conectar_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = st.secrets["connections"]["gsheets"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    client = gspread.authorize(creds)
    planilha = client.open_by_key("1U3XbcY2uGBNrcsQZDAEuo4O-9yH2-FuMUctsb11a69E")
    return planilha

def carregar_planilhas(planilha):
    """Carrega abas 'producao' e 'desperdicio'"""
    try:
        producao_ws = planilha.worksheet("producao")
        desperdicio_ws = planilha.worksheet("desperdicio")
        producao = pd.DataFrame(producao_ws.get_all_records())
        desperdicio = pd.DataFrame(desperdicio_ws.get_all_records())

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
        st.error(f"⚠️ Erro ao carregar planilhas: {e}")
        return pd.DataFrame(), pd.DataFrame()

def salvar_planilha(planilha, aba, df):
    """Atualiza uma aba específica da planilha"""
    try:
        ws = planilha.worksheet(aba)
        ws.clear()
        if not df.empty:
            ws.update([df.columns.values.tolist()] + df.values.tolist())
        else:
            ws.update([[""]])
    except Exception as e:
        st.error(f"⚠️ Erro ao salvar planilha ({aba}): {e}")

# ====================================
# INICIALIZAÇÃO
# ====================================
planilha = conectar_sheets()
producao, desperdicio = carregar_planilhas(planilha)

# ====================================
# FUNÇÕES AUXILIARES
# ====================================
def cor_do_dia(dia_semana):
    cores = ["azul","verde","amarelo","laranja","vermelho","prata","dourado"]
    return cores[dia_semana]

def emoji_cor(cor):
    mapa = {
        "azul": "🟦", "verde": "🟩", "amarelo": "🟨",
        "laranja": "🟧", "vermelho": "🟥", "prata": "⬜", "dourado": "🟨✨"
    }
    return mapa.get(cor, "⬛")

def gerar_alertas(producao):
    """Alertas de validade com 2 dias de antecedência"""
    hoje = datetime.now().date()
    alertas = []
    for _, row in producao.iterrows():
        if pd.isna(row["data_validade"]):
            continue
        validade = pd.to_datetime(row["data_validade"]).date()
        dias = (validade - hoje).days
        if dias == 2:
            alertas.append(f"⚠️ {row['produto']} ({emoji_cor(row['cor'])}) vence em 2 dias ({validade})")
        elif dias == 1:
            alertas.append(f"🟡 {row['produto']} ({emoji_cor(row['cor'])}) vence amanhã ({validade})")
        elif dias <= 0:
            alertas.append(f"❌ {row['produto']} ({emoji_cor(row['cor'])}) VENCIDO ({validade})")
    return alertas

def gerar_painel_validade(producao):
    """Gera dataframe visual com status de validade"""
    if producao.empty:
        return pd.DataFrame()

    producao["data_validade"] = pd.to_datetime(producao["data_validade"], errors="coerce")
    hoje = datetime.now()
    producao["dias_restantes"] = (producao["data_validade"] - hoje).dt.days
    producao["status"] = producao["dias_restantes"].apply(
        lambda d: "✅ Dentro do prazo" if d > 2 else ("⚠️ Perto do vencimento" if 0 < d <= 2 else "❌ Vencido")
    )
    return producao[["produto","cor","data_producao","data_validade","dias_restantes","status"]].sort_values("dias_restantes")

# ====================================
# INTERFACE PRINCIPAL
# ====================================
st.title("🏭 Controle de Produção e Desperdício")

menu = st.sidebar.radio(
    "Menu principal:",
    ["📊 Painel de Status", "Registrar Produção 🧁", "Registrar Desperdício ⚠️",
     "Gerenciar Validades ♻️", "Relatórios 📈",
     "Consultar Produção 🔍", "Zerar sistema 🧹"]
)

# ====================================
# ALERTAS NA LATERAL
# ====================================
st.sidebar.markdown("### 🔔 Alertas de Validade")
for alerta in gerar_alertas(producao):
    st.sidebar.warning(alerta)

# ====================================
# 0️⃣ PAINEL DE STATUS
# ====================================
if menu == "📊 Painel de Status":
    st.header("📊 Situação Atual dos Produtos")
    painel = gerar_painel_validade(producao)
    if painel.empty:
        st.info("Nenhum produto cadastrado ainda.")
    else:
        st.dataframe(painel, use_container_width=True)
        st.caption("📅 Atualizado em tempo real conforme planilha.")

# ====================================
# 1️⃣ REGISTRAR PRODUÇÃO
# ====================================
elif menu == "Registrar Produção 🧁":
    st.header("🧁 Registro de Produção")

    produto = st.text_input("Produto:")
    quantidade = st.number_input("Quantidade produzida:", min_value=1, step=1)
    if st.button("💾 Salvar Produção"):
        if produto.strip() == "":
            st.error("Informe o nome do produto.")
        else:
            data = datetime.now()
            cor = cor_do_dia(data.weekday())
            validade = (data + timedelta(days=3)).strftime("%Y-%m-%d")
            novo = {
                "id": len(producao) + 1,
                "data_producao": data.strftime("%Y-%m-%d"),
                "produto": produto.strip(),
                "cor": cor,
                "quantidade_produzida": quantidade,
                "data_remarcacao": "",
                "data_validade": validade
            }
            producao = pd.concat([producao, pd.DataFrame([novo])], ignore_index=True)
            salvar_planilha(planilha, "producao", producao)
            st.success(f"✅ Produção registrada com cor {emoji_cor(cor)} {cor.upper()}.")

# ====================================
# 2️⃣ REGISTRAR DESPERDÍCIO (com sugestão automática)
# ====================================
elif menu == "Registrar Desperdício ⚠️":
    st.header("⚠️ Registro de Desperdício")

    produto = st.text_input("Produto:")
    sugestao_cor = ""
    sugestao_id = ""
    sugestao_data = ""

    if produto.strip() != "":
        prod_rel = producao[producao["produto"].str.lower().str.contains(produto.lower(), na=False)]
        if not prod_rel.empty:
            ult = prod_rel.iloc[-1]
            sugestao_cor = ult["cor"]
            sugestao_id = ult["id"]
            sugestao_data = ult["data_producao"]
            st.info(f"🟢 Sugestão: Cor {emoji_cor(sugestao_cor)} ({sugestao_cor.upper()}), Lote {sugestao_id}, produzido em {sugestao_data}")
        else:
            st.warning("Nenhuma produção encontrada com esse nome.")

    quantidade = st.number_input("Quantidade desperdiçada:", min_value=1, step=1)
    motivo = st.text_area("Motivo:")

    if st.button("💾 Salvar Desperdício"):
        if produto.strip() == "":
            st.error("Digite o nome do produto.")
        elif sugestao_cor == "":
            st.error("Produto não encontrado na produção.")
        else:
            novo = {
                "id": len(desperdicio) + 1,
                "data_desperdicio": datetime.now().strftime("%Y-%m-%d"),
                "produto": produto.strip(),
                "cor": sugestao_cor,
                "quantidade_desperdicada": quantidade,
                "motivo": motivo,
                "id_producao": sugestao_id,
                "data_producao": sugestao_data
            }
            desperdicio = pd.concat([desperdicio, pd.DataFrame([novo])], ignore_index=True)
            salvar_planilha(planilha, "desperdicio", desperdicio)
            st.success(f"✅ Desperdício registrado ({emoji_cor(sugestao_cor)} {sugestao_cor.upper()}).")

# ====================================
# 7️⃣ ZERAR SISTEMA
# ====================================
elif menu == "Zerar sistema 🧹":
    st.header("🧹 Zerar Sistema")
    st.warning("⚠️ Esta ação apaga todos os dados das planilhas!")

    confirmar = st.checkbox("Confirmo que desejo apagar todos os dados.")
    if st.button("🚨 Zerar agora"):
        if confirmar:
            producao = producao.iloc[0:0]
            desperdicio = desperdicio.iloc[0:0]
            salvar_planilha(planilha, "producao", producao)
            salvar_planilha(planilha, "desperdicio", desperdicio)
            st.success("✅ Todos os dados foram apagados com sucesso!")
        else:
            st.warning("Marque a confirmação antes de apagar.")

# ====================================
# RODAPÉ
# ====================================
st.markdown("---")
st.caption("📘 Sistema de Controle de Produção e Desperdício - Versão 1.4 | Desenvolvido por Diogo Silva 💼")
