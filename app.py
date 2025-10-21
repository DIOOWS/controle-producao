import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
import plotly.express as px

# =======================
# CONFIGURAÇÕES GERAIS
# =======================
PRODUCAO_FILE = "producao.csv"
DESPERDICIO_FILE = "desperdicio.csv"

# Cores fixas da semana
CORES_DIAS = {
    "monday": "azul",
    "tuesday": "verde",
    "wednesday": "amarelo",
    "thursday": "laranja",
    "friday": "vermelho",
    "saturday": "prata",
    "sunday": "dourado"
}

# Emojis visuais das cores
def emoji_cor(cor):
    cores_emoji = {
        "azul": "🟦",
        "verde": "🟩",
        "amarelo": "🟨",
        "laranja": "🟧",
        "vermelho": "🟥",
        "prata": "",
        "dourado": "🟨✨"
    }
    return cores_emoji.get(str(cor).lower(), "⬜")

# Paleta de cores para gráficos
PALETA_CORES = {
    "azul": "#3498db",
    "verde": "#2ecc71",
    "amarelo": "#f1c40f",
    "laranja": "#e67e22",
    "vermelho": "#e74c3c",
    "prata": "#bdc3c7",
    "dourado": "#f5c542"
}

st.set_page_config(page_title="Controle de Produção", layout="wide", page_icon="📦")

# =======================
# FUNÇÕES AUXILIARES
# =======================
def carregar_csv(caminho, colunas):
    if os.path.exists(caminho):
        df = pd.read_csv(caminho)
        for col in colunas:
            if col not in df.columns:
                df[col] = ""
        return df
    else:
        return pd.DataFrame(columns=colunas)

def cor_por_data(data):
    dia_semana = data.strftime("%A").lower()
    return CORES_DIAS.get(dia_semana, "sem cor")

def sugestao_produtos():
    if os.path.exists(PRODUCAO_FILE):
        df = pd.read_csv(PRODUCAO_FILE)
        if "produto" in df.columns and not df.empty:
            return sorted(df["produto"].dropna().unique().tolist())
    return []

def verificar_alertas():
    """Verifica produtos próximos do vencimento"""
    if not os.path.exists(PRODUCAO_FILE):
        return []
    df = pd.read_csv(PRODUCAO_FILE)
    if "data_validade" not in df.columns:
        return []
    df["data_validade"] = pd.to_datetime(df["data_validade"], errors="coerce")
    hoje = datetime.now()
    alertas = []
    for _, row in df.iterrows():
        if pd.isna(row["data_validade"]):
            continue
        dias = (row["data_validade"] - hoje).days
        cor_emoji = emoji_cor(row.get("cor", ""))
        produto = row.get("produto", "")
        if dias < 0:
            alertas.append(f"❌ {produto} ({cor_emoji}) está VENCIDO — enviar para desperdício.")
        elif dias == 0:
            alertas.append(f"⚠️ {produto} ({cor_emoji}) vence HOJE — verificar remarcação.")
        elif dias == 1:
            alertas.append(f"🕒 {produto} ({cor_emoji}) vence AMANHÃ — atenção.")
        elif dias <= 3:
            alertas.append(f"⚠️ {produto} ({cor_emoji}) vence em {dias} dias.")
    return alertas

# =======================
# SIDEBAR DE ALERTAS
# =======================
st.sidebar.markdown("### ⏰ Alertas de Validade")
alertas = verificar_alertas()
if alertas:
    for a in alertas:
        st.sidebar.warning(a)
else:
    st.sidebar.success("✅ Nenhum produto próximo do vencimento.")

# =======================
# MENU PRINCIPAL
# =======================
menu = st.sidebar.radio(
    "📋 Menu",
    [
        "Registrar Produção",
        "Registrar Desperdício",
        "Gerenciar Validades ♻️",
        "Relatórios 📊",
        "Histórico detalhado 🕓",
        "Consultar Produção 🔍",
        "Excluir registros 🗑️",
        "Zerar sistema 🧹"
    ]
)

# =======================
# 1️⃣ REGISTRAR PRODUÇÃO
# =======================
if menu == "Registrar Produção":
    st.header("🧁 Registrar Produção")
    produto = st.text_input("Produto:")
    quantidade = st.number_input("Quantidade produzida:", min_value=1, step=1)
    data = st.date_input("Data de produção:", datetime.now())

    cor = cor_por_data(data)
    data_validade = data + timedelta(days=3)

    st.info(f"🎨 Cor automática: {emoji_cor(cor)} {cor.upper()} — Validade: {data_validade.strftime('%d/%m/%Y')}")

    if st.button("✅ Salvar Produção"):
        df = carregar_csv(PRODUCAO_FILE, ["id","data_producao","produto","cor","quantidade_produzida","data_remarcacao","data_validade"])
        novo_id = len(df) + 1
        novo = pd.DataFrame([{
            "id": novo_id,
            "data_producao": data.strftime("%Y-%m-%d"),
            "produto": produto.title(),
            "cor": cor,
            "quantidade_produzida": quantidade,
            "data_remarcacao": "",
            "data_validade": data_validade.strftime("%Y-%m-%d")
        }])
        df = pd.concat([df, novo], ignore_index=True)
        df.to_csv(PRODUCAO_FILE, index=False)
        st.success(f"✅ Produção registrada: {produto} - {quantidade} unidades - Cor: {cor.upper()}")
        st.balloons()

# =======================
# 2️⃣ REGISTRAR DESPERDÍCIO (automático)
# =======================
elif menu == "Registrar Desperdício":
    st.header("⚠️ Registrar Desperdício")

    produtos_cadastrados = sugestao_produtos()
    produto = st.selectbox("Produto (busque ou digite novo):", options=[""] + produtos_cadastrados, index=0)
    produto = produto.strip().title() if produto else ""
    quantidade = st.number_input("Quantidade desperdiçada:", min_value=1, step=1)
    motivo = st.text_area("Motivo:")

    if produto:
        prod = carregar_csv(PRODUCAO_FILE, ["id","data_producao","produto","cor","quantidade_produzida","data_validade"])
        producoes_produto = prod[prod["produto"].str.lower().str.contains(produto.lower(), na=False)]
        if not producoes_produto.empty:
            ultima = producoes_produto.iloc[-1]
            st.info(f"📦 Último lote: {emoji_cor(ultima['cor'])} {ultima['cor'].upper()} — {ultima['data_producao']}")
            st.session_state["ultima_producao_auto"] = ultima.to_dict()
        else:
            st.warning("⚠️ Nenhuma produção encontrada para esse produto.")
            st.session_state["ultima_producao_auto"] = None

    if st.button("⚠️ Salvar Desperdício"):
        ultima = st.session_state.get("ultima_producao_auto")
        if not produto:
            st.error("❌ Informe o produto.")
        elif ultima is None:
            st.error("⚠️ Nenhuma produção encontrada.")
        else:
            disp = carregar_csv(DESPERDICIO_FILE, ["id","data_desperdicio","produto","cor","quantidade_desperdicada","motivo","id_producao","data_producao"])
            novo_id = len(disp) + 1
            data_hoje = datetime.now().strftime("%Y-%m-%d")
            novo = pd.DataFrame([{
                "id": novo_id,
                "data_desperdicio": data_hoje,
                "produto": ultima["produto"],
                "cor": ultima["cor"],
                "quantidade_desperdicada": quantidade,
                "motivo": motivo,
                "id_producao": ultima["id"],
                "data_producao": ultima["data_producao"]
            }])
            disp = pd.concat([disp, novo], ignore_index=True)
            disp.to_csv(DESPERDICIO_FILE, index=False)
            st.success(f"⚠️ Desperdício salvo: {ultima['produto']} ({emoji_cor(ultima['cor'])} {ultima['cor'].upper()}) - {quantidade} unidades.")
            st.session_state["ultima_producao_auto"] = None
# =======================
# 3️⃣ GERENCIAR VALIDADES (remarcação)
# =======================
elif menu == "Gerenciar Validades ♻️":
    st.header("♻️ Remarcação de Produtos")

    prod = carregar_csv(PRODUCAO_FILE, [
        "id","data_producao","produto","cor","quantidade_produzida",
        "data_remarcacao","data_validade"
    ])

    if prod.empty:
        st.info("Nenhum produto encontrado.")
    else:
        hoje = datetime.now()
        prod["data_validade"] = pd.to_datetime(prod["data_validade"], errors="coerce")
        prod["dias_restantes"] = (prod["data_validade"] - hoje).dt.days
        prod["Status"] = prod["dias_restantes"].apply(
            lambda d: "✅ Dentro do prazo" if d > 1 else
            ("⚠️ Perto do vencimento" if d == 1 else "❌ Vencido")
        )
        prod["Cor (visual)"] = prod["cor"].apply(lambda c: f"{emoji_cor(c)} {c.title()}")

        st.dataframe(
            prod[["id","produto","Cor (visual)","data_producao","data_validade","dias_restantes","Status"]],
            use_container_width=True
        )

        id_remarcar = st.number_input("ID do produto para remarcar:", min_value=1, step=1)
        if st.button("♻️ Remarcar produto selecionado"):
            if id_remarcar in prod["id"].values:
                hoje = datetime.now()
                prod.loc[prod["id"] == id_remarcar, "data_remarcacao"] = hoje.strftime("%Y-%m-%d")
                prod.loc[prod["id"] == id_remarcar, "data_validade"] = (hoje + timedelta(days=1)).strftime("%Y-%m-%d")
                prod.to_csv(PRODUCAO_FILE, index=False)
                st.success("✅ Produto remarcado com novo prazo de 1 dia.")
            else:
                st.error("❌ ID não encontrado.")

# =======================
# 4️⃣ RELATÓRIOS 📊
# =======================
elif menu == "Relatórios 📊":
    st.header("📊 Relatório de Produção x Desperdício")

    if not os.path.exists(PRODUCAO_FILE):
        st.warning("Nenhuma produção registrada ainda.")
    else:
        prod = pd.read_csv(PRODUCAO_FILE)
        disp = carregar_csv(DESPERDICIO_FILE, [
            "id","data_desperdicio","produto","cor","quantidade_desperdicada",
            "motivo","id_producao","data_producao"
        ])

        resumo_prod = prod.groupby(["cor","produto"])["quantidade_produzida"].sum().reset_index()
        resumo_disp = disp.groupby(["cor","produto"])["quantidade_desperdicada"].sum().reset_index()

        resultado = pd.merge(resumo_prod, resumo_disp, on=["cor","produto"], how="left").fillna(0)
        resultado["% desperdício"] = (resultado["quantidade_desperdicada"] / resultado["quantidade_produzida"]) * 100
        resultado["Estoque atual"] = resultado["quantidade_produzida"] - resultado["quantidade_desperdicada"]
        resultado["Cor (visual)"] = resultado["cor"].apply(lambda c: f"{emoji_cor(c)} {c.title()}")

        st.dataframe(
            resultado[["Cor (visual)","produto","quantidade_produzida",
                       "quantidade_desperdicada","% desperdício","Estoque atual"]],
            use_container_width=True
        )

        if not resultado.empty:
            st.subheader("📉 Gráfico de Desperdício por Cor")
            graf = px.bar(
                resultado,
                x="cor",
                y="% desperdício",
                color="cor",
                text="% desperdício",
                title="Percentual de Desperdício por Cor",
                color_discrete_map=PALETA_CORES
            )
            graf.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
            st.plotly_chart(graf, use_container_width=True)

# =======================
# 5️⃣ HISTÓRICO DETALHADO 🕓
# =======================
elif menu == "Histórico detalhado 🕓":
    st.header("🕓 Histórico detalhado de lançamentos")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📦 Produção registrada")
        prod = carregar_csv(PRODUCAO_FILE, [
            "id","data_producao","produto","cor","quantidade_produzida",
            "data_remarcacao","data_validade"
        ])
        if prod.empty:
            st.info("Nenhuma produção registrada.")
        else:
            prod["Cor (visual)"] = prod["cor"].apply(lambda c: f"{emoji_cor(c)} {c.title()}")
            st.dataframe(
                prod[["id","data_producao","produto","Cor (visual)","quantidade_produzida","data_validade"]]
                .sort_values(by="data_producao", ascending=False),
                use_container_width=True
            )

    with col2:
        st.subheader("⚠️ Desperdício registrado")
        disp = carregar_csv(DESPERDICIO_FILE, [
            "id","data_desperdicio","produto","cor","quantidade_desperdicada",
            "motivo","id_producao","data_producao"
        ])
        if disp.empty:
            st.info("Nenhum desperdício registrado.")
        else:
            disp["Cor (visual)"] = disp["cor"].apply(lambda c: f"{emoji_cor(c)} {c.title()}")
            st.dataframe(
                disp[["id","data_desperdicio","produto","Cor (visual)",
                      "quantidade_desperdicada","motivo"]]
                .sort_values(by="data_desperdicio", ascending=False),
                use_container_width=True
            )
# =======================
# 6️⃣ CONSULTAR PRODUÇÃO 🔍
# =======================
elif menu == "Consultar Produção 🔍":
    st.header("🔍 Consultar produções registradas")

    produtos_cadastrados = sugestao_produtos()
    produto = st.selectbox("Produto (busque ou digite novo):", options=[""] + produtos_cadastrados, index=0)
    produto = produto.strip()
    cor = st.selectbox("Cor (lote):", ["Todas", "azul", "verde", "amarelo", "laranja", "vermelho", "prata", "dourado"])
    data_inicial = st.date_input("Data inicial:", datetime.now().replace(day=1))
    data_final = st.date_input("Data final:", datetime.now())

    if st.button("🔎 Buscar"):
        prod = carregar_csv(PRODUCAO_FILE, [
            "id","data_producao","produto","cor","quantidade_produzida","data_validade"
        ])
        if prod.empty:
            st.warning("⚠️ Nenhuma produção registrada ainda.")
        else:
            prod["data_producao"] = pd.to_datetime(prod["data_producao"])
            filtrado = prod[
                (prod["data_producao"] >= pd.to_datetime(data_inicial)) &
                (prod["data_producao"] <= pd.to_datetime(data_final))
            ]
            if produto:
                filtrado = filtrado[filtrado["produto"].str.lower().str.contains(produto.lower(), na=False)]
            if cor != "Todas":
                filtrado = filtrado[filtrado["cor"] == cor]

            if filtrado.empty:
                st.error("❌ Nenhuma produção encontrada nesse intervalo.")
            else:
                filtrado["Cor (visual)"] = filtrado["cor"].apply(lambda c: f"{emoji_cor(c)} {c.title()}")
                st.dataframe(
                    filtrado[["id","data_producao","produto","Cor (visual)","quantidade_produzida","data_validade"]],
                    use_container_width=True
                )
                total = filtrado["quantidade_produzida"].sum()
                st.info(f"📦 **Total produzido no período:** {int(total)} unidades")

# =======================
# 7️⃣ EXCLUIR REGISTROS 🗑️ (versão revisada e funcional)
# =======================
elif menu == "Excluir registros 🗑️":
    st.header("🗑️ Excluir lançamentos")

    tipo = st.radio("Escolha o tipo de registro:", ["Produção", "Desperdício"])

    # Carregar o arquivo certo
    if tipo == "Produção":
        caminho_arquivo = PRODUCAO_FILE
        df = carregar_csv(caminho_arquivo, [
            "id","data_producao","produto","cor","quantidade_produzida","data_validade"
        ])
    else:
        caminho_arquivo = DESPERDICIO_FILE
        df = carregar_csv(caminho_arquivo, [
            "id","data_desperdicio","produto","cor","quantidade_desperdicada",
            "motivo","id_producao","data_producao"
        ])

    # Se não houver registros
    if df.empty:
        st.warning("Nenhum registro encontrado.")
    else:
        df["id"] = pd.to_numeric(df["id"], errors="coerce").fillna(0).astype(int)
        df = df.sort_values(by="id", ascending=True)
        st.dataframe(df, use_container_width=True)

        id_excluir = st.number_input("Digite o ID que deseja excluir:", min_value=1, step=1)
        confirmar = st.checkbox("Confirmar exclusão permanente")

        if st.button("🗑️ Excluir registro selecionado"):
            id_excluir = int(id_excluir)

            if id_excluir not in df["id"].values:
                st.error("❌ ID não encontrado.")
            elif not confirmar:
                st.warning("Marque a caixa de confirmação antes de excluir.")
            else:
                # Remover o registro e reescrever o CSV
                df_filtrado = df[df["id"] != id_excluir].copy()

                # Reatribuir IDs sequenciais para evitar duplicação
                if not df_filtrado.empty:
                    df_filtrado["id"] = range(1, len(df_filtrado) + 1)

                df_filtrado.to_csv(caminho_arquivo, index=False)

                st.success(f"✅ Registro ID {id_excluir} excluído com sucesso!")
                st.info("Atualize a página para ver a lista atualizada.")




# =======================
# 8️⃣ ZERAR SISTEMA 🧹
# =======================
elif menu == "Zerar sistema 🧹":
    st.header("🧹 Zerar todos os dados do sistema")
    st.warning("⚠️ Esta ação irá APAGAR todos os registros de produção e desperdício permanentemente!")

    confirmar = st.checkbox("Confirmo que desejo apagar TODOS os dados.")
    if st.button("🧹 Zerar agora"):
        if confirmar:
            for file in [PRODUCAO_FILE, DESPERDICIO_FILE]:
                if os.path.exists(file):
                    os.remove(file)
            st.success("✅ Todos os dados foram apagados com sucesso! Sistema zerado.")
            st.toast("Sistema reiniciado com sucesso 🚀", icon="🧹")
        else:
            st.warning("Marque a caixa de confirmação antes de zerar.")
