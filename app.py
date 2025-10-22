import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
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
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["connections"]["gsheets"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        planilha = client.open_by_key("1U3XbcY2uGBNrcsQZDAEuo4O-9yH2-FuMUctsb11a69E")
        return planilha
    except Exception as e:
        st.error(f"❌ Erro ao conectar ao Google Sheets: {e}")
        return None


def carregar_planilhas(planilha):
    try:
        producao = pd.DataFrame(planilha.worksheet("producao").get_all_records())
        desperdicio = pd.DataFrame(planilha.worksheet("desperdicio").get_all_records())
        usuarios = pd.DataFrame(planilha.worksheet("usuarios").get_all_records())

        if producao.empty:
            producao = pd.DataFrame(columns=["id", "data_producao", "produto", "cor",
                                             "quantidade_produzida", "data_remarcacao", "data_validade"])
        if desperdicio.empty:
            desperdicio = pd.DataFrame(columns=["id", "data_desperdicio", "produto", "cor",
                                                "quantidade_desperdicada", "motivo", "id_producao", "data_producao"])
        return producao, desperdicio, usuarios
    except Exception as e:
        st.error(f"❌ Erro ao carregar planilhas: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


def salvar_planilha_segura(planilha, aba, df):
    try:
        ws = planilha.worksheet(aba)
        ws.clear()
        if not df.empty:
            ws.update([df.columns.values.tolist()] + df.values.tolist())
    except Exception as e:
        st.error(f"❌ Erro ao salvar na aba {aba}: {e}")


def atualizar_linha(planilha, aba, linha, dados):
    """Atualiza apenas uma linha específica, convertendo datas para strings."""
    try:
        dados_convertidos = {}
        for k, v in dados.items():
            if isinstance(v, (pd.Timestamp, datetime)):
                dados_convertidos[k] = v.strftime("%Y-%m-%d")
            else:
                dados_convertidos[k] = str(v)

        ws = planilha.worksheet(aba)
        colunas = ws.row_values(1)
        valores = [dados_convertidos.get(c, "") for c in colunas]

        ws.update(f"A{linha}:G{linha}", [valores[:7]])
        st.info(f"✅ Linha {linha} atualizada com sucesso.")
    except Exception as e:
        st.error(f"❌ Erro ao atualizar linha na aba {aba}: {e}")

# ====================================
# FUNÇÕES AUXILIARES
# ====================================
def cor_do_dia(dia_semana):
    cores = ["azul", "verde", "amarelo", "laranja", "vermelho", "prata", "dourado"]
    return cores[dia_semana]

def dia_da_cor(cor):
    mapa = {
        "azul": "Segunda-feira", "verde": "Terça-feira", "amarelo": "Quarta-feira",
        "laranja": "Quinta-feira", "vermelho": "Sexta-feira", "prata": "Sábado", "dourado": "Domingo"
    }
    return mapa.get(cor, "?")

def emoji_cor(cor):
    mapa = {"azul": "🟦", "verde": "🟩", "amarelo": "🟨", "laranja": "🟧",
            "vermelho": "🟥", "prata": "⬜", "dourado": "🟨✨"}
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
# LOGIN
# ====================================
def login_page(planilha):
    st.title("🔐 Login no Sistema")

    producao, desperdicio, usuarios = carregar_planilhas(planilha)
    usuario = st.text_input("Usuário:")
    senha = st.text_input("Senha:", type="password")

    if st.button("Entrar"):
        user = usuarios[(usuarios["usuario"] == usuario) & (usuarios["senha"] == senha)]
        if not user.empty:
            st.session_state["logado"] = True
            st.session_state["usuario"] = usuario
            st.session_state["tipo"] = user.iloc[0].get("tipo", "usuario")
            st.success(f"Bem-vindo(a), {user.iloc[0]['nome']} 👋")
            st.rerun()
        else:
            st.error("Usuário ou senha incorretos.")

# ====================================
# APP PRINCIPAL
# ====================================
def main_app(planilha):
    producao, desperdicio, usuarios = carregar_planilhas(planilha)

    st.sidebar.markdown(f"👤 Usuário: **{st.session_state['usuario']}**")
    st.sidebar.markdown(f"🔐 Tipo: **{st.session_state['tipo']}**")
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    menu = st.sidebar.radio(
        "Menu principal:",
        ["📊 Painel de Status", "Registrar Produção 🧁", "Registrar Desperdício ⚠️",
         "♻️ Remarcar Produtos", "Relatórios 📈", "Zerar Sistema 🧹"]
    )

    st.sidebar.markdown("### 🔔 Alertas de Validade")
    for alerta in gerar_alertas(producao):
        st.sidebar.warning(alerta)

    # PAINEL
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
            st.dataframe(producao[["id","produto","cor","data_producao","data_validade","dias_restantes","status"]])

    # PRODUÇÃO
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
                validade = (data + timedelta(days=2)).strftime("%Y-%m-%d")
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
                salvar_planilha_segura(planilha, "producao", producao)
                st.success(f"✅ Produção registrada com cor {emoji_cor(cor)} {cor.upper()} ({dia_da_cor(cor)}).")

    # DESPERDÍCIO
    elif menu == "Registrar Desperdício ⚠️":
        st.header("⚠️ Registrar Desperdício")

        produto = st.text_input("Buscar produto:")
        if produto.strip():
            prod_rel = producao[
                (producao["produto"].str.lower().str.contains(produto.lower(), na=False)) &
                (pd.to_datetime(producao["data_validade"]) >= datetime.now())
            ]

            if not prod_rel.empty:
                st.success(f"{len(prod_rel)} produto(s) encontrados dentro do prazo.")
                opcoes = [
                    f"ID {row['id']} - {row['produto']} ({emoji_cor(row['cor'])} {row['cor']}) - {dia_da_cor(row['cor'])}"
                    for _, row in prod_rel.iterrows()
                ]
                selecao = st.selectbox("Selecione o produto:", opcoes)

                id_sel = int(selecao.split(" ")[1])
                prod_sel = prod_rel[prod_rel["id"] == id_sel].iloc[0]

                st.info(f"🟢 {prod_sel['produto']} ({emoji_cor(prod_sel['cor'])} {prod_sel['cor'].upper()} - {dia_da_cor(prod_sel['cor'])})")

                quantidade = st.number_input("Quantidade desperdiçada:", min_value=1, step=1)
                motivo = st.text_area("Motivo do desperdício:")

                if st.button("💾 Registrar Desperdício"):
                    novo = {
                        "id": len(desperdicio) + 1,
                        "data_desperdicio": datetime.now().strftime("%Y-%m-%d"),
                        "produto": prod_sel["produto"],
                        "cor": prod_sel["cor"],
                        "quantidade_desperdicada": quantidade,
                        "motivo": motivo,
                        "id_producao": prod_sel["id"],
                        "data_producao": prod_sel["data_producao"]
                    }
                    desperdicio = pd.concat([desperdicio, pd.DataFrame([novo])], ignore_index=True)
                    salvar_planilha_segura(planilha, "desperdicio", desperdicio)
                    st.success(f"✅ Desperdício registrado ({emoji_cor(prod_sel['cor'])} {prod_sel['cor']}).")
            else:
                st.warning("Nenhum produto encontrado dentro do prazo.")
        else:
            st.info("Digite parte do nome do produto para buscar.")

    # REMARCAÇÃO
    elif menu == "♻️ Remarcar Produtos":
        st.header("♻️ Remarcação de Produtos")
        if producao.empty:
            st.info("Nenhum produto cadastrado.")
        else:
            producao["data_validade"] = pd.to_datetime(producao["data_validade"], errors="coerce")
            producao["dias_restantes"] = (producao["data_validade"] - datetime.now()).dt.days
            exp = producao[producao["dias_restantes"] <= 2]

            if exp.empty:
                st.success("✅ Nenhum produto perto do vencimento.")
            else:
                st.dataframe(exp[["id","produto","cor","data_producao","data_validade","dias_restantes"]])
                id_remarcar = st.number_input("Informe o ID do produto:", min_value=1, step=1)
                dias_extra = st.number_input("Dias para nova validade:", min_value=1, step=1, value=2)

                if st.button("♻️ Aplicar Remarcação"):
                    if id_remarcar in producao["id"].values:
                        hoje = datetime.now()
                        nova_validade = (hoje + timedelta(days=dias_extra)).strftime("%Y-%m-%d")

                        producao.loc[producao["id"] == id_remarcar, "data_remarcacao"] = hoje.strftime("%Y-%m-%d")
                        producao.loc[producao["id"] == id_remarcar, "data_validade"] = nova_validade

                        linha_planilha = int(producao.loc[producao["id"] == id_remarcar].index[0]) + 2
                        dados_atualizados = producao.loc[producao["id"] == id_remarcar].iloc[0].to_dict()
                        atualizar_linha(planilha, "producao", linha_planilha, dados_atualizados)

                        st.success(f"✅ Produto ID {id_remarcar} remarcado até {nova_validade}.")
                    else:
                        st.error("❌ ID não encontrado.")

    # ZERAR
    elif menu == "Zerar Sistema 🧹":
        st.header("🧹 Zerar Sistema")
        if st.session_state["tipo"] != "admin":
            st.warning("⚠️ Apenas o ADMIN pode zerar o sistema.")
        else:
            confirmar = st.checkbox("Confirmo que desejo apagar todos os dados.")
            if st.button("🚨 Zerar agora"):
                if confirmar:
                    producao = producao.iloc[0:0]
                    desperdicio = desperdicio.iloc[0:0]
                    salvar_planilha_segura(planilha, "producao", producao)
                    salvar_planilha_segura(planilha, "desperdicio", desperdicio)
                    st.success("✅ Todos os dados foram apagados com sucesso!")
                else:
                    st.warning("Marque a confirmação antes de apagar.")

# ====================================
# EXECUÇÃO
# ====================================
planilha = conectar_sheets()
if planilha:
    if "logado" not in st.session_state or not st.session_state["logado"]:
        login_page(planilha)
    else:
        main_app(planilha)
