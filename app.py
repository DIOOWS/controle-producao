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
# LOGIN DE USUÁRIOS
# ====================================
USUARIOS = {
    "admin": {"senha": "1234", "nome": "Administrador"},
    "producao": {"senha": "senha123", "nome": "Equipe de Produção"}
}

def login_page():
    st.title("🔐 Login - Controle de Produção")
    usuario = st.text_input("Usuário:")
    senha = st.text_input("Senha:", type="password")

    if st.button("Entrar"):
        if usuario in USUARIOS and USUARIOS[usuario]["senha"] == senha:
            st.session_state["usuario"] = usuario
            st.session_state["autenticado"] = True
            st.success("✅ Login realizado com sucesso!")
            st.experimental_rerun()
        else:
            st.error("Usuário ou senha incorretos.")

if "autenticado" not in st.session_state or not st.session_state["autenticado"]:
    login_page()
    st.stop()

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

def carregar_planilhas(planilha):
    try:
        producao = pd.DataFrame(planilha.worksheet("producao").get_all_records())
        desperdicio = pd.DataFrame(planilha.worksheet("desperdicio").get_all_records())
        if producao.empty:
            producao = pd.DataFrame(columns=["id","data_producao","produto","cor","quantidade_produzida","data_remarcacao","data_validade"])
        if desperdicio.empty:
            desperdicio = pd.DataFrame(columns=["id","data_desperdicio","produto","cor","quantidade_desperdicada","motivo","id_producao","data_producao"])
        return producao, desperdicio
    except Exception as e:
        st.error(f"❌ Erro ao carregar planilhas: {e}")
        return pd.DataFrame(), pd.DataFrame()

def salvar_planilha(planilha, aba, df):
    try:
        ws = planilha.worksheet(aba)
        ws.clear()
        ws.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        st.error(f"❌ Erro ao salvar na aba {aba}: {e}")

planilha = conectar_sheets()
if planilha is None:
    st.stop()
producao, desperdicio = carregar_planilhas(planilha)

# ====================================
# FUNÇÕES AUXILIARES
# ====================================
def cor_do_dia(dia_semana):
    return ["azul","verde","amarelo","laranja","vermelho","prata","dourado"][dia_semana]

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
    mapa = {"azul":"🟦","verde":"🟩","amarelo":"🟨","laranja":"🟧","vermelho":"🟥","prata":"⬜","dourado":"🟨✨"}
    return mapa.get(cor, "⬛")

def gerar_alertas(producao):
    hoje = datetime.now().date()
    alertas = []
    for _, row in producao.iterrows():
        if pd.isna(row["data_validade"]): continue
        validade = pd.to_datetime(row["data_validade"]).date()
        dias = (validade - hoje).days
        if dias == 2:
            alertas.append(f"⚠️ {row['produto']} ({emoji_cor(row['cor'])}) vence em 2 dias ({validade})")
        elif dias == 1:
            alertas.append(f"🟡 {row['produto']} ({emoji_cor(row['cor'])}) vence amanhã ({validade})")
        elif dias <= 0:
            alertas.append(f"❌ {row['produto']} ({emoji_cor(row['cor'])}) VENCIDO ({validade})")
    return alertas

# ====================================
# INTERFACE PRINCIPAL
# ====================================
st.title("🏭 Controle de Produção e Desperdício")
st.sidebar.success(f"👋 Bem-vindo, {USUARIOS[st.session_state['usuario']]['nome']}")

menu = st.sidebar.radio(
    "Menu principal:",
    ["📊 Painel de Status", "Registrar Produção 🧁", "Registrar Desperdício ⚠️", "Relatórios 📈", "Zerar sistema 🧹"]
)

st.sidebar.markdown("### 🔔 Alertas de Validade")
for alerta in gerar_alertas(producao):
    st.sidebar.warning(alerta)

# ====================================
# PAINEL DE STATUS
# ====================================
if menu == "📊 Painel de Status":
    st.header("📊 Situação Atual")
    if producao.empty:
        st.info("Nenhum produto cadastrado ainda.")
    else:
        producao["data_validade"] = pd.to_datetime(producao["data_validade"], errors="coerce")
        hoje = datetime.now()
        producao["dias_restantes"] = (producao["data_validade"] - hoje).dt.days
        producao["status"] = producao["dias_restantes"].apply(
            lambda d: "✅ Dentro do prazo" if d > 2 else ("⚠️ Perto do vencimento" if 0 < d <= 2 else "❌ Vencido")
        )
        producao["dia_cor"] = producao["cor"].apply(dia_da_cor)
        st.dataframe(producao[["produto","cor","dia_cor","data_producao","data_validade","dias_restantes","status"]])

# ====================================
# REGISTRAR PRODUÇÃO
# ====================================
elif menu == "Registrar Produção 🧁":
    st.header("🧁 Registrar Produção")
    produto = st.text_input("Produto:")
    quantidade = st.number_input("Quantidade produzida:", min_value=1, step=1)
    if st.button("💾 Salvar Produção"):
        if produto.strip() == "":
            st.error("Digite o nome do produto.")
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
            st.success(f"✅ Produção registrada com cor {emoji_cor(cor)} {cor.upper()} ({dia_da_cor(cor)}).")

# ====================================
# REGISTRAR DESPERDÍCIO AVANÇADO
# ====================================
elif menu == "Registrar Desperdício ⚠️":
    st.header("⚠️ Registrar Desperdício")
    produto = st.text_input("Produto:")

    if produto.strip():
        hoje = datetime.now().date()
        disponiveis = producao[
            (producao["produto"].str.contains(produto, case=False, na=False)) &
            (pd.to_datetime(producao["data_validade"]).dt.date >= hoje)
        ]

        if disponiveis.empty:
            st.warning("❌ Nenhum lote válido encontrado.")
        else:
            disponiveis["dia_cor"] = disponiveis["cor"].apply(dia_da_cor)
            st.dataframe(disponiveis[["id","produto","cor","dia_cor","data_producao","data_validade","quantidade_produzida"]])
            lote = st.number_input("Selecione o ID do lote:", min_value=1, step=1)

            if lote in disponiveis["id"].values:
                registro = disponiveis[disponiveis["id"] == lote].iloc[0]
                st.info(f"🟢 Lote {lote} selecionado: Cor {emoji_cor(registro['cor'])} {registro['cor'].upper()} ({dia_da_cor(registro['cor'])}), Produzido em {registro['data_producao']}")
                quantidade = st.number_input("Quantidade desperdiçada:", min_value=1, step=1)
                motivo = st.text_area("Motivo:")
                if st.button("💾 Salvar Desperdício"):
                    novo = {
                        "id": len(desperdicio) + 1,
                        "data_desperdicio": datetime.now().strftime("%Y-%m-%d"),
                        "produto": registro["produto"],
                        "cor": registro["cor"],
                        "quantidade_desperdicada": quantidade,
                        "motivo": motivo,
                        "id_producao": registro["id"],
                        "data_producao": registro["data_producao"]
                    }
                    desperdicio = pd.concat([desperdicio, pd.DataFrame([novo])], ignore_index=True)
                    salvar_planilha(planilha, "desperdicio", desperdicio)
                    st.success(f"✅ Desperdício registrado ({emoji_cor(registro['cor'])} {registro['cor'].upper()} - {dia_da_cor(registro['cor'])}).")

# ====================================
# RELATÓRIOS
# ====================================
elif menu == "Relatórios 📈":
    st.header("📈 Relatórios")
    if producao.empty:
        st.warning("Nenhum dado disponível.")
    else:
        inicio = st.date_input("Data inicial", datetime.now().date() - timedelta(days=7))
        fim = st.date_input("Data final", datetime.now().date())

        prod_filtro = producao[pd.to_datetime(producao["data_producao"]).dt.date.between(inicio, fim)]
        disp_filtro = desperdicio[pd.to_datetime(desperdicio["data_desperdicio"]).dt.date.between(inicio, fim)]

        total_prod = prod_filtro["quantidade_produzida"].sum()
        total_disp = disp_filtro["quantidade_desperdicada"].sum()
        perc = (total_disp / total_prod * 100) if total_prod > 0 else 0

        c1, c2, c3 = st.columns(3)
        c1.metric("Produzido", int(total_prod))
        c2.metric("Desperdiçado", int(total_disp))
        c3.metric("% Desperdício", f"{perc:.1f}%")

        prod_filtro["dia_cor"] = prod_filtro["cor"].apply(dia_da_cor)
        resumo_prod = prod_filtro.groupby(["cor","dia_cor","produto"])["quantidade_produzida"].sum().reset_index()
        resumo_disp = disp_filtro.groupby(["cor","produto"])["quantidade_desperdicada"].sum().reset_index()
        resultado = pd.merge(resumo_prod, resumo_disp, on=["cor","produto"], how="left").fillna(0)
        resultado["% desperdício"] = (resultado["quantidade_desperdicada"] / resultado["quantidade_produzida"]) * 100
        st.dataframe(resultado)
        fig = px.bar(resultado, x="produto", y="% desperdício", color="dia_cor", text="% desperdício", title="Desperdício por Produto e Dia da Cor")
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)

# ====================================
# ZERAR SISTEMA
# ====================================
elif menu == "Zerar sistema 🧹":
    st.header("🧹 Zerar Sistema")
    st.warning("⚠️ Esta ação apaga todos os dados!")
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
st.caption("📘 Sistema de Controle de Produção e Desperdício - Versão 1.6 | Desenvolvido por Diogo Silva 💼")
