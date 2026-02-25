import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# ========================================
# CONFIGURAÇÃO DA PÁGINA
# ========================================

st.set_page_config(
    page_title="Dashboard Inteligente de Gastos",
    layout="wide",
    page_icon="💳"
)

# ========================================
# CARREGAR DADOS
# ========================================

@st.cache_data
def carregar_dados():
    df = pd.read_csv("gastos_consolidados_final.csv")

    if 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
        df['Mes'] = df['Data'].dt.to_period('M').astype(str)
        df['Dia_Semana'] = df['Data'].dt.day_name()

    return df

df = carregar_dados()

st.title("💳 Dashboard Inteligente de Gastos")

# ========================================
# FILTROS
# ========================================

col1, col2 = st.columns(2)

with col1:

    opcoes = ["Resumo Total"] + sorted(df['Arquivo'].dropna().unique().tolist())

    fatura_selecionada = st.selectbox(
        "📅 Selecione a fatura:",
        opcoes
    )

with col2:

    if 'Categoria' in df.columns:

        categorias = ["Todas"] + sorted(df['Categoria'].dropna().unique().tolist())

        categoria_selecionada = st.selectbox(
            "🏷️ Categoria:",
            categorias
        )

    else:
        categoria_selecionada = "Todas"

# ========================================
# FILTRAGEM
# ========================================

if fatura_selecionada == "Resumo Total":
    df_filtrado = df.copy()
else:
    df_filtrado = df[df['Arquivo'] == fatura_selecionada]

if categoria_selecionada != "Todas" and 'Categoria' in df.columns:
    df_filtrado = df_filtrado[df_filtrado['Categoria'] == categoria_selecionada]

# somente gastos positivos
gastos_positivos = df_filtrado[df_filtrado['Valor (R$)'] > 0]

# ========================================
# KPIs
# ========================================

st.subheader("📊 Visão Geral")

total_gasto = gastos_positivos['Valor (R$)'].sum()

qtd_transacoes = len(gastos_positivos)

ticket_medio = total_gasto / qtd_transacoes if qtd_transacoes > 0 else 0

maior_compra = gastos_positivos['Valor (R$)'].max() if qtd_transacoes > 0 else 0

# comparação mês anterior

variacao = 0

if fatura_selecionada != "Resumo Total":

    idx = opcoes.index(fatura_selecionada)

    if idx > 1:

        anterior = opcoes[idx-1]

        df_anterior = df[df['Arquivo'] == anterior]

        total_anterior = df_anterior[df_anterior['Valor (R$)'] > 0]['Valor (R$)'].sum()

        if total_anterior > 0:
            variacao = ((total_gasto - total_anterior) / total_anterior) * 100

col1, col2, col3, col4 = st.columns(4)

col1.metric("💰 Total Gasto", f"R$ {total_gasto:,.2f}", f"{variacao:+.1f}%")

col2.metric("🛒 Transações", qtd_transacoes)

col3.metric("📊 Ticket Médio", f"R$ {ticket_medio:,.2f}")

col4.metric("🔝 Maior Compra", f"R$ {maior_compra:,.2f}")

st.divider()

# ========================================
# PARETO 80/20
# ========================================

st.subheader("🎯 Concentração de Gastos")

pareto = gastos_positivos.groupby('Descrição')['Valor (R$)'].sum().sort_values(ascending=False).reset_index()

pareto['%'] = pareto['Valor (R$)'] / total_gasto * 100

pareto['%_acumulado'] = pareto['%'].cumsum()

col1, col2 = st.columns(2)

with col1:

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=pareto['Descrição'][:10],
        y=pareto['Valor (R$)'][:10],
        name="Gasto"
    ))

    fig.add_trace(go.Scatter(
        x=pareto['Descrição'][:10],
        y=pareto['%_acumulado'][:10],
        yaxis="y2",
        name="% acumulado"
    ))

    fig.update_layout(
        yaxis2=dict(overlaying='y', side='right')
    )

    st.plotly_chart(fig, use_container_width=True)

with col2:

    top1 = pareto.iloc[0]

    top3 = pareto.head(3)['%'].sum()

    top5 = pareto.head(5)['%'].sum()

    st.metric("Maior fonte", top1['Descrição'], f"{top1['%']:.1f}%")

    st.metric("Top 3", f"{top3:.1f}%")

    st.metric("Top 5", f"{top5:.1f}%")

st.divider()

# ========================================
# EVOLUÇÃO TEMPORAL
# ========================================

st.subheader("📈 Evolução")

evolucao = df[df['Valor (R$)'] > 0].groupby('Arquivo')['Valor (R$)'].sum().reset_index()

fig = px.line(
    evolucao,
    x='Arquivo',
    y='Valor (R$)',
    markers=True
)

st.plotly_chart(fig, use_container_width=True)

# ========================================
# PREVISÃO
# ========================================

st.subheader("🔮 Previsão")

media = evolucao['Valor (R$)'].mean()

tendencia = evolucao['Valor (R$)'].diff().mean()

previsao = media + tendencia

col1, col2 = st.columns(2)

col1.metric("Próximo mês", f"R$ {previsao:,.2f}")

col2.metric("Projeção anual", f"R$ {previsao*12:,.2f}")

st.divider()

# ========================================
# OUTLIERS
# ========================================

media_valor = gastos_positivos['Valor (R$)'].mean()

desvio = gastos_positivos['Valor (R$)'].std()

outliers = gastos_positivos[gastos_positivos['Valor (R$)'] > media_valor + 2*desvio]

# ========================================
# SCORE FINANCEIRO
# ========================================

st.subheader("🧠 Score Financeiro")

score = 100

if variacao > 20:
    score -= 15

if len(outliers) > 0:
    score -= 15

concentracao = pareto.iloc[0]['%']

if concentracao > 40:
    score -= 20

score = max(score, 0)

fig = go.Figure(go.Indicator(
    mode="gauge+number",
    value=score,
    gauge={'axis': {'range': [0, 100]}}
))

st.plotly_chart(fig, use_container_width=True)

# ========================================
# RISCO
# ========================================

st.subheader("⚠️ Risco")

if concentracao > 50:
    st.error("Risco Alto")
elif concentracao > 30:
    st.warning("Risco Moderado")
else:
    st.success("Risco Baixo")

st.divider()

# ========================================
# TABELA
# ========================================

st.subheader("🔍 Transações")

st.dataframe(
    gastos_positivos.sort_values(
        'Valor (R$)',
        ascending=False
    )
)

# ========================================
# CHAT LOCAL
# ========================================

st.subheader("🤖 Assistente")

pergunta = st.text_input("Pergunte algo:")

def responder(pergunta):

    pergunta = pergunta.lower()

    if "onde gasto mais" in pergunta:

        top = pareto.iloc[0]

        return f"Você gasta mais em {top['Descrição']} (R$ {top['Valor (R$)']:,.2f})"

    if "total" in pergunta:

        return f"Total gasto: R$ {total_gasto:,.2f}"

    if "score" in pergunta:

        return f"Seu score é {score}/100"

    if "economizar" in pergunta:

        economia = pareto.iloc[0]['Valor (R$)'] * 0.2

        return f"Você pode economizar R$ {economia:,.2f}"

    return "Pergunta não reconhecida"

if pergunta:

    st.success(responder(pergunta))