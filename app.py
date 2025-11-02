import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import time
from io import BytesIO

# ====================================
# CONFIGURAÇÃO DA PÁGINA
# ====================================
st.set_page_config(page_title="Controle de Produção e Desperdício", page_icon="🏭", layout="wide")

# ====================================
# CONEXÃO E CARREGAMENTO OTIMIZADOS
# ====================================

@st.cache_resource
def conectar_sheets():
    """Conecta ao Google Sheets apenas uma vez."""
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


@st.cache_data(ttl=600)
def carregar_planilhas(planilha):
    """Lê as abas do Sheets e mantém cache por 10 minutos."""
    try:
        abas = {ws.title: ws.get_all_records() for ws in planilha.worksheets()}

        producao = pd.DataFrame(abas.get("producao", []))
        desperdicio = pd.DataFrame(abas.get("desperdicio", []))
        usuarios = pd.DataFrame(abas.get("usuarios", []))

        # Estrutura padrão
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
    """Salva os dados com delay e segurança."""
    try:
        ws = planilha.worksheet(aba)
        ws.clear()
        time.sleep(1)
        if not df.empty:
            ws.update([df.columns.values.tolist()] + df.values.tolist())
        st.success(f"✅ Dados salvos com sucesso na aba '{aba}'.")
    except Exception as e:
        st.error(f"❌ Erro ao salvar na aba {aba}: {e}")


def atualizar_linha(planilha, aba, linha, dados):
    """Atualiza apenas uma linha específica."""
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

    # ====================================
    # CABEÇALHO DE ATUALIZAÇÃO + BOTÃO MANUAL
    # ====================================
    ultima_atualizacao = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    st.markdown(
        f"""
        <div style="background-color:#e8f4ff;padding:10px;border-radius:8px;margin-bottom:10px;">
            <b>🔄 Dados atualizados a cada 10 minutos.</b><br>
            Última atualização: <span style="color:#0073e6;">{ultima_atualizacao}</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button("🔁 Atualizar Agora"):
        st.cache_data.clear()
        st.experimental_rerun()

    # ====================================
    # MENU LATERAL
    # ====================================
    st.sidebar.markdown(f"👤 Usuário: **{st.session_state['usuario']}**")
    st.sidebar.markdown(f"🔐 Tipo: **{st.session_state['tipo']}**")
    if st.sidebar.button("Sair"):
        st.session_state.clear()
        st.rerun()

    menu = st.sidebar.radio(
        "Menu principal:",
        ["📊 Painel de Status", "Registrar Produção 🧁", "Registrar Desperdício ⚠️",
         "♻️ Remarcar Produtos", "Relatórios 📈", "📤 Exportar Relatórios", "Zerar Sistema 🧹"]
    )

    st.sidebar.markdown("### 🔔 Alertas de Validade")
    for alerta in gerar_alertas(producao):
        st.sidebar.warning(alerta)

    # ====================================
    # PAINEL
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
            st.dataframe(producao[["id","produto","cor","data_producao","data_validade","dias_restantes","status"]])

    # ====================================
    # RELATÓRIOS
    # ====================================
    elif menu == "Relatórios 📈":
        st.header("📈 Relatórios de Produção e Desperdício")
        aba = st.radio("Escolha o tipo de relatório:", ["Produção", "Desperdício"])

        if aba == "Produção":
            if producao.empty:
                st.info("Nenhuma produção registrada.")
            else:
                st.subheader("📊 Produção total por produto")
                df_prod = producao.groupby("produto")["quantidade_produzida"].sum().reset_index()
                df_prod = df_prod.sort_values(by="quantidade_produzida", ascending=False)
                st.dataframe(df_prod)
                st.bar_chart(df_prod.set_index("produto"))

        elif aba == "Desperdício":
            if desperdicio.empty:
                st.info("Nenhum desperdício registrado.")
            else:
                st.subheader("⚠️ Quantidade desperdiçada por produto")
                df_desp = desperdicio.groupby("produto")["quantidade_desperdicada"].sum().reset_index()
                df_desp = df_desp.sort_values(by="quantidade_desperdicada", ascending=False)
                st.dataframe(df_desp)
                st.bar_chart(df_desp.set_index("produto"))

    # ====================================
    # EXPORTAR RELATÓRIOS
    # ====================================
    elif menu == "📤 Exportar Relatórios":
        st.header("📤 Exportar Relatórios em Excel ou CSV")

        tipo = st.radio("Escolha o que exportar:", ["Produção", "Desperdício"])
        formato = st.radio("Formato do arquivo:", ["Excel (.xlsx)", "CSV (.csv)"])

        df = producao.copy() if tipo == "Produção" else desperdicio.copy()

        if df.empty:
            st.warning("⚠️ Nenhum dado disponível para exportação.")
        else:
            nome_arquivo = f"{tipo.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if formato == "Excel (.xlsx)":
                buffer = BytesIO()
                with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                    df.to_excel(writer, index=False, sheet_name=tipo)
                st.download_button(
                    label="📥 Baixar Excel",
                    data=buffer.getvalue(),
                    file_name=f"{nome_arquivo}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            else:
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Baixar CSV",
                    data=csv,
                    file_name=f"{nome_arquivo}.csv",
                    mime="text/csv"
                )

    # ====================================
    # ZERAR SISTEMA
    # ====================================
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
