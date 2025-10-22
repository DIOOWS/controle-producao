import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import plotly.express as px

# ====================================
# CONFIGURAÇÃO GERAL
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
        st.error(f"❌ Erro de conexão com o Google Sheets: {e}")
        return None


def carregar_ou_criar_aba(planilha, nome_aba, colunas):
    try:
        ws = planilha.worksheet(nome_aba)
        df = pd.DataFrame(ws.get_all_records())
        if df.empty:
            df = pd.DataFrame(columns=colunas)
        return df
    except gspread.exceptions.WorksheetNotFound:
        planilha.add_worksheet(title=nome_aba, rows="100", cols=str(len(colunas)))
        ws = planilha.worksheet(nome_aba)
        ws.append_row(colunas)
        return pd.DataFrame(columns=colunas)


def salvar_planilha(planilha, aba, df):
    try:
        ws = planilha.worksheet(aba)
        ws.clear()
        if not df.empty:
            ws.update([df.columns.values.tolist()] + df.values.tolist())
        else:
            ws.update([[""]])
    except Exception as e:
        st.error(f"❌ Erro ao salvar na aba {aba}: {e}")

# ====================================
# LOGIN
# ====================================
def login_page(planilha):
    st.title("🔐 Login - Controle de Produção e Desperdício")

    usuarios = carregar_ou_criar_aba(planilha, "usuarios", ["usuario", "senha", "nome", "tipo"])

    usuario = st.text_input("Usuário:")
    senha = st.text_input("Senha:", type="password")

    if st.button("Entrar"):
        user = usuarios[(usuarios["usuario"] == usuario) & (usuarios["senha"] == senha)]
        if not user.empty:
            st.session_state["logado"] = True
            st.session_state["usuario"] = usuario
            st.session_state["tipo"] = user.iloc[0]["tipo"]
            st.success(f"✅ Bem-vindo, {user.iloc[0]['nome']}!")
            st.experimental_rerun()
        else:
            st.error("❌ Usuário ou senha incorretos.")

    st.divider()
    with st.expander("👤 Criar novo usuário"):
        novo_user = st.text_input("Novo usuário:")
        nova_senha = st.text_input("Nova senha:", type="password")
        nome = st.text_input("Nome completo:")
        if st.button("Registrar usuário"):
            if novo_user in usuarios["usuario"].values:
                st.error("⚠️ Usuário já existe.")
            else:
                novo = {"usuario": novo_user, "senha": nova_senha, "nome": nome, "tipo": "usuario"}
                usuarios = pd.concat([usuarios, pd.DataFrame([novo])], ignore_index=True)
                salvar_planilha(planilha, "usuarios", usuarios)
                st.success("✅ Usuário cadastrado com sucesso! Faça login.")

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
    return mapa.get(cor, "Desconhecido")

def emoji_cor(cor):
    mapa = {"azul": "🟦", "verde": "🟩", "amarelo": "🟨", "laranja": "🟧", "vermelho": "🟥", "prata": "⬜", "dourado": "🟨✨"}
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
# APLICAÇÃO PRINCIPAL
# ====================================
def main_app(planilha):
    producao = carregar_ou_criar_aba(planilha, "producao", [
        "id", "data_producao", "produto", "cor", "quantidade_produzida", "data_remarcacao", "data_validade"
    ])
    desperdicio = carregar_ou_criar_aba(planilha, "desperdicio", [
        "id", "data_desperdicio", "produto", "cor", "quantidade_desperdicada", "motivo", "id_producao", "data_producao"
    ])

    st.sidebar.title("Menu Principal")
    usuario = st.session_state.get("usuario", "desconhecido")
    st.sidebar.write(f"👤 Usuário: **{usuario}**")
    if st.sidebar.button("🚪 Sair"):
        st.session_state.clear()
        st.experimental_rerun()

    menu = st.sidebar.radio("Selecione:", [
        "📊 Painel de Status", "Registrar Produção 🧁", "Registrar Desperdício ⚠️",
        "♻️ Remarcar Produtos", "Relatórios 📈", "Zerar sistema 🧹"
    ])

    # --- ALERTAS ---
    st.sidebar.markdown("### 🔔 Alertas de Validade")
    for alerta in gerar_alertas(producao):
        st.sidebar.warning(alerta)

    # --- PAINEL ---
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
            st.dataframe(producao[["id", "produto", "cor", "data_producao", "data_validade", "dias_restantes", "status"]])

    # --- PRODUÇÃO ---
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
                salvar_planilha(planilha, "producao", producao)
                st.success(f"✅ Produção registrada ({emoji_cor(cor)} {cor.upper()} - {dia_da_cor(cor)}).")

    # --- DESPERDÍCIO ---
    elif menu == "Registrar Desperdício ⚠️":
        st.header("⚠️ Registrar Desperdício")
        produto = st.text_input("Produto:")
        if produto.strip():
            prod_rel = producao[
                (producao["produto"].str.lower().str.contains(produto.lower(), na=False)) &
                (pd.to_datetime(producao["data_validade"]) >= datetime.now())
            ]
            if not prod_rel.empty:
                st.dataframe(prod_rel[["id", "produto", "cor", "data_producao", "data_validade"]])
                ult = prod_rel.iloc[-1]
                st.info(f"Sugerido: {emoji_cor(ult['cor'])} {ult['cor']} ({dia_da_cor(ult['cor'])}) | Produzido em {ult['data_producao']}")
                quantidade = st.number_input("Quantidade desperdiçada:", min_value=1, step=1)
                motivo = st.text_area("Motivo:")
                if st.button("💾 Salvar Desperdício"):
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
                    salvar_planilha(planilha, "desperdicio", desperdicio)
                    st.success(f"✅ Desperdício registrado ({emoji_cor(ult['cor'])} {ult['cor']}).")
            else:
                st.warning("Nenhum produto válido encontrado com esse nome.")

    # --- REMARCAR ---
    elif menu == "♻️ Remarcar Produtos":
        st.header("♻️ Remarcação de Produtos")
        if producao.empty:
            st.info("Nenhum produto encontrado.")
        else:
            producao["data_validade"] = pd.to_datetime(producao["data_validade"], errors="coerce")
            producao["dias_restantes"] = (producao["data_validade"] - datetime.now()).dt.days
            exp = producao[producao["dias_restantes"] <= 2]
            if exp.empty:
                st.info("Nenhum produto perto do vencimento.")
            else:
                st.dataframe(exp[["id", "produto", "cor", "data_producao", "data_validade", "dias_restantes"]])
                id_remarcar = st.number_input("ID para remarcar:", min_value=1, step=1)
                dias_extra = st.number_input("Dias adicionais de validade:", min_value=1, step=1)
                if st.button("♻️ Remarcar"):
                    if id_remarcar in producao["id"].values:
                        hoje = datetime.now()
                        nova_validade = (hoje + timedelta(days=dias_extra)).strftime("%Y-%m-%d")
                        producao.loc[producao["id"] == id_remarcar, "data_remarcacao"] = hoje.strftime("%Y-%m-%d")
                        producao.loc[producao["id"] == id_remarcar, "data_validade"] = nova_validade
                        salvar_planilha(planilha, "producao", producao)
                        st.success(f"✅ Produto {id_remarcar} remarcado para {nova_validade}.")
                    else:
                        st.error("ID não encontrado.")

    # --- RELATÓRIOS ---
    elif menu == "Relatórios 📈":
        st.header("📈 Relatórios de Produção x Desperdício")
        if producao.empty:
            st.warning("Nenhum dado disponível.")
        else:
            col1, col2 = st.columns(2)
            inicio = col1.date_input("Data inicial", datetime.now().date() - timedelta(days=7))
            fim = col2.date_input("Data final", datetime.now().date())

            prod_filtro = producao[pd.to_datetime(producao["data_producao"]).dt.date.between(inicio, fim)]
            disp_filtro = desperdicio[pd.to_datetime(desperdicio["data_desperdicio"]).dt.date.between(inicio, fim)]

            total_prod = prod_filtro["quantidade_produzida"].sum()
            total_disp = disp_filtro["quantidade_desperdicada"].sum()
            perc = (total_disp / total_prod * 100) if total_prod > 0 else 0

            c1, c2, c3 = st.columns(3)
            c1.metric("Produzido", int(total_prod))
            c2.metric("Desperdiçado", int(total_disp))
            c3.metric("% Desperdício", f"{perc:.1f}%")

            resumo_prod = prod_filtro.groupby(["cor","produto"])["quantidade_produzida"].sum().reset_index()
            resumo_disp = disp_filtro.groupby(["cor","produto"])["quantidade_desperdicada"].sum().reset_index()
            resultado = pd.merge(resumo_prod, resumo_disp, on=["cor","produto"], how="left").fillna(0)
            resultado["% desperdício"] = (resultado["quantidade_desperdicada"] / resultado["quantidade_produzida"]) * 100
            st.dataframe(resultado)

            graf = px.bar(resultado, x="produto", y="% desperdício", color="cor", text="% desperdício")
            graf.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(graf, use_container_width=True)

    # --- ZERAR ---
    elif menu == "Zerar sistema 🧹":
        st.header("🧹 Zerar Sistema")
        if st.session_state.get("tipo") != "admin":
            st.error("❌ Apenas o administrador pode usar esta função.")
        else:
            st.warning("⚠️ Esta ação apaga todos os dados!")
            confirmar = st.checkbox("Confirmo que desejo apagar tudo.")
            if st.button("🚨 Zerar agora"):
                if confirmar:
                    producao = producao.iloc[0:0]
                    desperdicio = desperdicio.iloc[0:0]
                    salvar_planilha(planilha, "producao", producao)
                    salvar_planilha(planilha, "desperdicio", desperdicio)
                    st.success("✅ Dados apagados com sucesso!")
                else:
                    st.warning("Marque a confirmação antes de prosseguir.")


# ====================================
# EXECUÇÃO
# ====================================
planilha = conectar_sheets()
if planilha:
    if "logado" not in st.session_state or not st.session_state["logado"]:
        login_page(planilha)
    else:
        main_app(planilha)
