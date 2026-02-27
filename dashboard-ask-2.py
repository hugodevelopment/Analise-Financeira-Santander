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


     # 🔥 CONVERSÃO DA COLUNA VALOR
    if 'Valor (R$)' in df.columns:
        df['Valor (R$)'] = (
            df['Valor (R$)']
            .astype(str)
            .str.replace('R$', '', regex=False)
            .str.replace('.', '', regex=False)
            .str.replace(',', '.', regex=False)
            .str.strip()
        )

        df['Valor (R$)'] = pd.to_numeric(df['Valor (R$)'], errors='coerce')

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
# 🤖 AGENTE INTELIGENTE LOCAL
# ========================================

st.subheader("🤖 Assistente Financeiro Inteligente")

pergunta = st.text_input("Pergunte qualquer coisa sobre seus gastos:")

# ========================================
# INTENÇÕES SUPORTADAS
# ========================================

def detectar_intencao(texto):

    texto = texto.lower()

    intents = {

        "maior_gasto": [
            "onde gasto mais",
            "maior gasto",
            "gasto mais",
            "quem recebe mais dinheiro"
        ],

        "total": [
            "total",
            "quanto gastei",
            "valor total",
            "gasto total"
        ],

        "media": [
            "media",
            "médio",
            "ticket medio"
        ],

        "contagem": [
            "quantas compras",
            "quantas transações",
            "quantidade"
        ],

        "score": [
            "score",
            "nota financeira"
        ],

        "risco": [
            "risco",
            "perigo financeiro"
        ],

        "economizar": [
            "economizar",
            "como economizar",
            "reduzir gastos"
        ],

        "previsao": [
            "previsão",
            "projeção",
            "quanto vou gastar"
        ],

        "categoria": [
            "categoria",
            "qual categoria gasto mais"
        ]
    }

    for intent, palavras in intents.items():

        for palavra in palavras:

            if palavra in texto:
                return intent

    return "desconhecido"


# ========================================
# EXECUTOR
# ========================================

def executar_intencao(intent):

    if intent == "maior_gasto":

        top = pareto.iloc[0]

        return f"Você gasta mais em {top['Descrição']}, totalizando R$ {top['Valor (R$)']:,.2f}"

    elif intent == "total":

        return f"Seu gasto total foi R$ {total_gasto:,.2f}"

    elif intent == "media":

        return f"Seu gasto médio por compra é R$ {ticket_medio:,.2f}"

    elif intent == "contagem":

        return f"Você fez {qtd_transacoes} transações"

    elif intent == "score":

        if score >= 80:
            nivel = "excelente"
        elif score >= 60:
            nivel = "bom"
        else:
            nivel = "precisa melhorar"

        return f"Seu score financeiro é {score}/100, considerado {nivel}"

    elif intent == "risco":

        if concentracao > 50:
            return "Seu risco financeiro é alto devido à alta concentração de gastos"

        elif concentracao > 30:
            return "Seu risco financeiro é moderado"

        else:
            return "Seu risco financeiro é baixo"

    elif intent == "economizar":

        top = pareto.iloc[0]

        economia = top['Valor (R$)'] * 0.2

        return f"Se reduzir 20% dos gastos em {top['Descrição']}, economizaria R$ {economia:,.2f}"

    elif intent == "previsao":

        return f"Sua previsão de gasto mensal é R$ {previsao:,.2f}"

    elif intent == "categoria":

        if 'Categoria' in gastos_positivos.columns:

            cat = gastos_positivos.groupby('Categoria')['Valor (R$)'].sum().idxmax()

            valor = gastos_positivos.groupby('Categoria')['Valor (R$)'].sum().max()

            return f"Sua categoria com maior gasto é {cat}, com R$ {valor:,.2f}"

        else:
            return "Seu dataset não possui categorias"

    else:

        return gerar_resposta_generica()

# ========================================
# 🎯 ANÁLISE PROFUNDA DE PRIORIDADE FINANCEIRA
# ========================================

st.subheader("🎯 Análise de Prioridade Financeira")

# ============================================
# 2. FEATURE ENGINEERING
# ============================================

agrupado = df.groupby("Descrição").agg(
    total=("Valor (R$)", "sum"),
    frequencia=("Valor (R$)", "count"),
    media=("Valor (R$)", "mean"),
    meses_unicos=("mes", "nunique"),
    maior_compra=("Valor (R$)", "max")
)

# impacto mensal REAL
agrupado["impacto_mensal"] = agrupado["total"] / agrupado["meses_unicos"]

# ============================================
# 3. NORMALIZAÇÃO
# ============================================

def normalizar(coluna):
    min_val = coluna.min()
    max_val = coluna.max()
    
    if max_val == min_val:
        return coluna * 0
    
    return (coluna - min_val) / (max_val - min_val)

agrupado["total_norm"] = normalizar(agrupado["total"])
agrupado["freq_norm"] = normalizar(agrupado["frequencia"])
agrupado["media_norm"] = normalizar(agrupado["media"])
agrupado["impacto_norm"] = normalizar(agrupado["impacto_mensal"])

# ============================================
# 4. SCORE DE PRIORIDADE
# ============================================

agrupado["score"] = (
    0.4 * agrupado["impacto_norm"] +
    0.3 * agrupado["total_norm"] +
    0.2 * agrupado["freq_norm"] +
    0.1 * agrupado["media_norm"]
)

# ============================================
# 5. CLASSIFICAÇÃO
# ============================================

def classificar(score):

    if score >= 0.75:
        return "CRITICO"
    
    elif score >= 0.55:
        return "ALTO"
    
    elif score >= 0.35:
        return "MEDIO"
    
    else:
        return "BAIXO"

agrupado["prioridade"] = agrupado["score"].apply(classificar)

# ============================================
# 6. ECONOMIA POTENCIAL REALISTA
# ============================================

def potencial_economia(prioridade):

    if prioridade == "CRITICO":
        return 0.30
    
    elif prioridade == "ALTO":
        return 0.20
    
    elif prioridade == "MEDIO":
        return 0.10
    
    else:
        return 0.05

agrupado["economia_percentual"] = agrupado["prioridade"].apply(potencial_economia)

agrupado["economia_mensal"] = (
    agrupado["impacto_mensal"] *
    agrupado["economia_percentual"]
)

# ============================================
# 7. ORDENAR POR PRIORIDADE
# ============================================

agrupado = agrupado.sort_values("score", ascending=False)

# ============================================
# 8. RESULTADO FINAL
# ============================================

print("\n===== ANALISE DE PRIORIDADE DE GASTOS =====\n")

for descricao, row in agrupado.iterrows():

    print(f"{descricao}")
    print(f"  Impacto mensal real: R$ {row['impacto_mensal']:.2f}")
    print(f"  Maior compra: R$ {row['maior_compra']:.2f}")
    print(f"  Frequência: {row['frequencia']}")
    print(f"  Score: {row['score']:.2f}")
    print(f"  Prioridade: {row['prioridade']}")
    print(f"  Economia possível: R$ {row['economia_mensal']:.2f}/mês")
    print()

# ============================================
# 9. RESUMO FINAL
# ============================================

economia_total = agrupado["economia_mensal"].sum()

print("=====================================")
print(f"ECONOMIA TOTAL POSSÍVEL: R$ {economia_total:.2f}/mês")
print(f"ECONOMIA TOTAL POSSÍVEL: R$ {economia_total * 12:.2f}/ano")
print("=====================================")

# ============================================
# 10. TOP 5 MAIORES PRIORIDADES
# ============================================

print("\n===== TOP PRIORIDADES =====\n")

top5 = agrupado.head(5)

for descricao, row in top5.iterrows():

    print(f"Ação recomendada: reduzir gastos em {descricao}")
    print(f"Impacto mensal: R$ {row['impacto_mensal']:.2f}")
    print(f"Economia possível: R$ {row['economia_mensal']:.2f}/mês")
    print(f"Prioridade: {row['prioridade']}")
    print()

# ========================================
# EXECUÇÃO
# ========================================

if pergunta:

    intent = detectar_intencao(pergunta)

    resposta = executar_intencao(intent)

    st.success(resposta)