import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import gspread
from oauth2client.service_account import ServiceAccountCredentials

st.set_page_config(page_title="Controle de Produção e Desperdício", page_icon="🏭", layout="wide")

# ===============================
# CONEXÃO DIRETA COM GOOGLE SHEETS (via gspread)
# ===============================
def conectar_sheets():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name("credenciais.json", scope)
    client = gspread.authorize(creds)
    planilha = client.open_by_key("1U3XbcY2uGBNrcsQZDAEuo4O-9yH2-FuMUctsb11a69E")
    return planilha

def carregar_planilhas(planilha):
    """Carrega as abas de produção e desperdício do Sheets."""
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
        st.error(f"Erro ao carregar planilhas: {e}")
        return pd.DataFrame(), pd.DataFrame()

def salvar_planilha(planilha, aba, df):
    """Atualiza uma aba específica da planilha."""
    try:
        ws = planilha.worksheet(aba)
        ws.clear()
        ws.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        st.error(f"Erro ao salvar planilha: {e}")


# ===============================
# FUNÇÕES AUXILIARES
# ===============================
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
    """Gera alertas automáticos de validade."""
    hoje = datetime.now().date()
    alertas = []
    for _, row in producao.iterrows():
        if pd.isna(row["data_validade"]):
            continue
        validade = pd.to_datetime(row["data_validade"]).date()
        dias = (validade - hoje).days
        if dias == 3:
            alertas.append(f"⚠️ {row['produto']} ({emoji_cor(row['cor'])}) vence em 3 dias ({validade})")
        elif dias == 1:
            alertas.append(f"🟡 {row['produto']} ({emoji_cor(row['cor'])}) vence amanhã ({validade})")
        elif dias <= 0:
            alertas.append(f"❌ {row['produto']} ({emoji_cor(row['cor'])}) VENCIDO ({validade})")
    return alertas

# ===============================
# INTERFACE PRINCIPAL
# ===============================
st.title("🏭 Controle de Produção e Desperdício")

producao, desperdicio = carregar_planilhas()

menu = st.sidebar.radio(
    "Menu principal:",
    ["Registrar Produção 🧁", "Registrar Desperdício ⚠️",
     "Gerenciar Validades ♻️", "Relatórios 📊",
     "Consultar Produção 🔍", "Histórico detalhado 🕓", "Zerar sistema 🧹"]
)

# ===============================
# ALERTAS NA LATERAL
# ===============================
st.sidebar.markdown("### 🔔 Alertas de Validade")
for alerta in gerar_alertas(producao):
    st.sidebar.warning(alerta)

# ===============================
# 1️⃣ REGISTRAR PRODUÇÃO
# ===============================
if menu == "Registrar Produção 🧁":
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
            salvar_planilha("producao", producao)
            st.success(f"✅ Produção registrada com cor {emoji_cor(cor)} {cor.upper()}.")

# ===============================
# 2️⃣ REGISTRAR DESPERDÍCIO
# ===============================
elif menu == "Registrar Desperdício ⚠️":
    st.header("⚠️ Registro de Desperdício")

    produto = st.text_input("Produto:")
    quantidade = st.number_input("Quantidade desperdiçada:", min_value=1, step=1)
    motivo = st.text_area("Motivo:")

    if st.button("💾 Salvar Desperdício"):
        prod_rel = producao[producao["produto"].str.lower().str.contains(produto.lower(), na=False)]
        if prod_rel.empty:
            st.error("❌ Nenhuma produção encontrada para este produto.")
        else:
            ult = prod_rel.iloc[-1]
            novo = {
                "id": len(desperdicio) + 1,
                "data_desperdicio": datetime.now().strftime("%Y-%m-%d"),
                "produto": ult["produto"],
                "cor": ult["cor"],
                "quantidade_desperdicada": quantidade,
                "motivo": motivo,
                "id_producao": ult["id"],
                "data_producao": ult["data_producao"]
            }
            desperdicio = pd.concat([desperdicio, pd.DataFrame([novo])], ignore_index=True)
            salvar_planilha("desperdicio", desperdicio)
            st.success(f"✅ Desperdício registrado ({emoji_cor(ult['cor'])} {ult['cor']}).")
# ===============================
# 3️⃣ REMARCAR PRODUTOS
# ===============================
elif menu == "Gerenciar Validades ♻️":
    st.header("♻️ Remarcação de Produtos")
    if producao.empty:
        st.info("Nenhum produto encontrado.")
    else:
        producao["data_validade"] = pd.to_datetime(producao["data_validade"], errors="coerce")
        producao["dias_restantes"] = (producao["data_validade"] - datetime.now()).dt.days
        producao["status"] = producao["dias_restantes"].apply(
            lambda d: "✅ Dentro do prazo" if d > 1 else ("⚠️ Perto do vencimento" if d == 1 else "❌ Vencido")
        )
        st.dataframe(producao[["id","produto","cor","data_producao","data_validade","dias_restantes","status"]])

        id_remarcar = st.number_input("ID para remarcar:", min_value=1, step=1)
        if st.button("♻️ Remarcar"):
            if id_remarcar in producao["id"].values:
                hoje = datetime.now()
                producao.loc[producao["id"] == id_remarcar, "data_remarcacao"] = hoje.strftime("%Y-%m-%d")
                producao.loc[producao["id"] == id_remarcar, "data_validade"] = (hoje + timedelta(days=1)).strftime("%Y-%m-%d")
                salvar_planilha("producao", producao)
                st.success("✅ Produto remarcado com sucesso.")
            else:
                st.error("ID não encontrado.")

# ===============================
# 4️⃣ RELATÓRIOS
# ===============================
elif menu == "Relatórios 📊":
    st.header("📊 Relatórios de Produção x Desperdício")

    if producao.empty:
        st.warning("Nenhum dado registrado ainda.")
    else:
        # ========== NOVO: Resumo da Semana ==========
        st.subheader("📅 Resumo da Semana")
        hoje = datetime.now().date()
        semana_inicio = hoje - timedelta(days=7)

        prod_semana = producao[pd.to_datetime(producao["data_producao"]).dt.date >= semana_inicio]
        disp_semana = desperdicio[pd.to_datetime(desperdicio["data_desperdicio"]).dt.date >= semana_inicio]

        total_prod = prod_semana["quantidade_produzida"].sum()
        total_disp = disp_semana["quantidade_desperdicada"].sum()
        perc = (total_disp / total_prod * 100) if total_prod > 0 else 0

        col1, col2, col3 = st.columns(3)
        col1.metric("Produzido na semana", int(total_prod))
        col2.metric("Desperdiçado na semana", int(total_disp))
        col3.metric("% Desperdício", f"{perc:.1f}%")

        st.divider()

        # ========== Relatório Detalhado ==========
        resumo_prod = producao.groupby(["cor","produto"])["quantidade_produzida"].sum().reset_index()
        resumo_disp = desperdicio.groupby(["cor","produto"])["quantidade_desperdicada"].sum().reset_index()

        resultado = pd.merge(resumo_prod, resumo_disp, on=["cor","produto"], how="left").fillna(0)
        resultado["% desperdício"] = (resultado["quantidade_desperdicada"] / resultado["quantidade_produzida"]) * 100
        st.dataframe(resultado)

        graf = px.bar(resultado, x="produto", y="% desperdício", color="cor", text="% desperdício")
        graf.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(graf, use_container_width=True)

# ===============================
# 5️⃣ CONSULTAR PRODUÇÃO (NOVO)
# ===============================
elif menu == "Consultar Produção 🔍":
    st.header("🔍 Consulta de Produção por Produto")

    termo = st.text_input("Digite parte do nome do produto:")

    if termo.strip() != "":
        filtro = producao[producao["produto"].str.lower().str.contains(termo.lower(), na=False)]
        if filtro.empty:
            st.warning("Nenhum produto encontrado.")
        else:
            st.success(f"{len(filtro)} registro(s) encontrado(s):")
            st.dataframe(filtro[["id","data_producao","produto","cor","quantidade_produzida","data_validade"]])

            # Permitir exclusão individual
            st.markdown("### 🗑️ Excluir registro")
            id_excluir = st.number_input("ID para excluir:", min_value=1, step=1)
            if st.button("❌ Excluir Produção"):
                if id_excluir in filtro["id"].values:
                    producao = producao[producao["id"] != id_excluir]
                    salvar_planilha("producao", producao)
                    st.success("✅ Registro de produção excluído com sucesso.")
                else:
                    st.error("ID não encontrado neste filtro.")
    else:
        st.info("Digite parte do nome para buscar.")
# ===============================
# 6️⃣ HISTÓRICO DETALHADO
# ===============================
elif menu == "Histórico detalhado 🕓":
    st.header("🕓 Histórico completo")
    st.subheader("📦 Produção")
    if producao.empty:
        st.info("Nenhum registro de produção encontrado.")
    else:
        st.dataframe(producao.sort_values(by="data_producao", ascending=False))

    st.subheader("⚠️ Desperdício")
    if desperdicio.empty:
        st.info("Nenhum registro de desperdício encontrado.")
    else:
        st.dataframe(desperdicio.sort_values(by="data_desperdicio", ascending=False))

    # Permitir exclusão de registros de desperdício
    st.markdown("### 🗑️ Excluir registro de desperdício")
    id_excluir = st.number_input("ID para excluir (desperdício):", min_value=1, step=1)
    if st.button("❌ Excluir Desperdício"):
        if id_excluir in desperdicio["id"].values:
            desperdicio = desperdicio[desperdicio["id"] != id_excluir]
            salvar_planilha("desperdicio", desperdicio)
            st.success("✅ Registro de desperdício excluído com sucesso.")
        else:
            st.error("ID não encontrado.")

# ===============================
# 7️⃣ ZERAR SISTEMA
# ===============================
elif menu == "Zerar sistema 🧹":
    st.header("🧹 Zerar Sistema")
    st.warning("⚠️ Esta ação irá apagar permanentemente todos os dados das planilhas!")

    confirmar = st.checkbox("Confirmo que desejo apagar todos os dados.")
    if st.button("🚨 Zerar agora"):
        if confirmar:
            producao = producao.iloc[0:0]
            desperdicio = desperdicio.iloc[0:0]
            salvar_planilha("producao", producao)
            salvar_planilha("desperdicio", desperdicio)
            st.success("✅ Todos os dados foram apagados com sucesso!")
        else:
            st.warning("Marque a confirmação antes de apagar.")

# ===============================
# FIM DO APP
# ===============================
st.markdown("---")
st.caption("📘 Sistema de Controle de Produção e Desperdício - Versão 1.1 | Desenvolvido por Diogo Silva 💼")
