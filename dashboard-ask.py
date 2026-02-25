import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# ========================================
# CONFIGURAÇÃO DA PÁGINA
# ========================================
st.set_page_config(page_title="Dashboard Cartão", layout="wide", page_icon="💳")

# ========================================
# CARREGAR DADOS
# ========================================
df = pd.read_csv("gastos_consolidados_final.csv")

# Converter data se necessário
if 'Data' in df.columns:
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    df['Mes'] = df['Data'].dt.to_period('M').astype(str)
    df['Dia_Semana'] = df['Data'].dt.day_name()

st.title("💳 Dashboard Inteligente de Gastos do Cartão")

# ========================================
# FILTROS
# ========================================
col1, col2 = st.columns(2)
with col1:
    opcoes = ["Resumo Total"] + sorted(df['Arquivo'].dropna().unique().tolist())
    fatura_selecionada = st.selectbox("📅 Selecione a fatura:", opcoes)

with col2:
    if 'Categoria' in df.columns:
        categorias = ["Todas"] + sorted(df['Categoria'].dropna().unique().tolist())
        categoria_selecionada = st.selectbox("🏷️ Categoria:", categorias)
    else:
        categoria_selecionada = "Todas"

# Base filtrada
if fatura_selecionada == "Resumo Total":
    df_filtrado = df.copy()
else:
    df_filtrado = df[df['Arquivo'] == fatura_selecionada]

if categoria_selecionada != "Todas" and 'Categoria' in df.columns:
    df_filtrado = df_filtrado[df_filtrado['Categoria'] == categoria_selecionada]

# ========================================
# 1. CARDS DE KPIs PRINCIPAIS
# ========================================
st.subheader("📊 Visão Geral")

gastos_positivos = df_filtrado[df_filtrado['Valor (R$)'] > 0]
total_gasto = gastos_positivos['Valor (R$)'].sum()
print(f"Total gasto calculado: R$ {total_gasto:,.2f}")
qtd_transacoes = len(gastos_positivos)
ticket_medio = total_gasto / qtd_transacoes if qtd_transacoes > 0 else 0
maior_compra = gastos_positivos['Valor (R$)'].max() if len(gastos_positivos) > 0 else 0

# Comparação com mês anterior
if fatura_selecionada != "Resumo Total" and len(opcoes) > 2:
    idx_atual = opcoes.index(fatura_selecionada)
    if idx_atual > 1:
        fatura_anterior = opcoes[idx_atual - 1]
        df_anterior = df[df['Arquivo'] == fatura_anterior]
        total_anterior = df_anterior[df_anterior['Valor (R$)'] > 0]['Valor (R$)'].sum()
        variacao = ((total_gasto - total_anterior) / total_anterior * 100) if total_anterior > 0 else 0
    else:
        variacao = 0
else:
    variacao = 0

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("💰 Total Gasto", f"R$ {total_gasto:,.2f}", delta=f"{variacao:+.1f}%" if variacao != 0 else None)
with col2:
    st.metric("🛒 Transações", f"{qtd_transacoes}", delta=None)
with col3:
    st.metric("📊 Ticket Médio", f"R$ {ticket_medio:,.2f}", delta=None)
with col4:
    st.metric("🔝 Maior Compra", f"R$ {maior_compra:,.2f}", delta=None)

st.divider()

# ========================================
# 2. ANÁLISE DE FREQUÊNCIA E PADRÕES
# ========================================
col1, col2 = st.columns(2)

with col1:
    st.subheader("📅 Frequência de Gastos por Dia da Semana")
    if 'Dia_Semana' in df_filtrado.columns:
        ordem_dias = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        nomes_dias = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        
        freq_dia = gastos_positivos.groupby('Dia_Semana')['Valor (R$)'].agg(['sum', 'count']).reset_index()
        freq_dia['Dia_Semana'] = pd.Categorical(freq_dia['Dia_Semana'], categories=ordem_dias, ordered=True)
        freq_dia = freq_dia.sort_values('Dia_Semana')
        freq_dia['Dia_PT'] = nomes_dias[:len(freq_dia)]
        
        fig = px.bar(freq_dia, x='Dia_PT', y='sum', labels={'sum': 'Total (R$)', 'Dia_PT': 'Dia da Semana'}, color='sum', color_continuous_scale='Blues')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Adicione uma coluna 'Data' para ver esta análise")

with col2:
    st.subheader("🏪 Top 5 Estabelecimentos")
    top_estab = gastos_positivos.groupby('Descrição')['Valor (R$)'].sum().reset_index()
    top_estab['%_TOTAL'] = (top_estab['Valor (R$)'] / total_gasto) * 100
    top_estab = top_estab.sort_values(by='Valor (R$)', ascending=False).head(5)
    
    fig = px.bar(top_estab, x='Valor (R$)', y='Descrição', orientation='h', text='%_TOTAL', labels={'Valor (R$)': 'Total Gasto', 'Descrição': 'Estabelecimento'})
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ========================================
# 3. EVOLUÇÃO TEMPORAL E TENDÊNCIAS
# ========================================
st.subheader("📈 Evolução e Tendências")

if fatura_selecionada == "Resumo Total":
    evolucao = df[df['Valor (R$)'] > 0].groupby('Arquivo').agg({'Valor (R$)': ['sum', 'count', 'mean']}).reset_index()
    evolucao.columns = ['Fatura', 'Total', 'Qtd', 'Ticket_Medio']
    evolucao['Variacao_%'] = evolucao['Total'].pct_change() * 100
    
    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=evolucao['Fatura'], y=evolucao['Total'], mode='lines+markers', name='Total Gasto', fill='tozeroy', line=dict(color='#1f77b4', width=3)))
        fig.update_layout(title='Evolução dos Gastos Mensais', xaxis_title='Mês', yaxis_title='Total (R$)', hovermode='x unified')
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        evolucao['Media_Movel_3'] = evolucao['Total'].rolling(window=3, min_periods=1).mean()
        fig = go.Figure()
        fig.add_trace(go.Bar(x=evolucao['Fatura'], y=evolucao['Total'], name='Gasto Mensal', marker_color='lightblue'))
        fig.add_trace(go.Scatter(x=evolucao['Fatura'], y=evolucao['Media_Movel_3'], name='Média Móvel (3 meses)', line=dict(color='red', width=2, dash='dash')))
        fig.update_layout(title='Gastos vs Média Móvel', xaxis_title='Mês', yaxis_title='Valor (R$)')
        st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(
        evolucao.style.format({'Total': 'R$ {:,.2f}', 'Ticket_Medio': 'R$ {:,.2f}', 'Variacao_%': '{:+.1f}%'}).background_gradient(subset=['Variacao_%'], cmap='RdYlGn', vmin=-20, vmax=20),
        use_container_width=True,
        hide_index=True
    )

st.divider()

# ========================================
# 4. ALERTAS E INSIGHTS INTELIGENTES
# ========================================
st.subheader("🚨 Alertas e Insights")

insights = []

# Detectar gastos atípicos
if len(gastos_positivos) > 0:
    media = gastos_positivos['Valor (R$)'].mean()
    desvio = gastos_positivos['Valor (R$)'].std()
    outliers = gastos_positivos[gastos_positivos['Valor (R$)'] > (media + 2 * desvio)]
    
    if len(outliers) > 0:
        insights.append({'tipo': '⚠️ Atenção', 'mensagem': f'Detectadas {len(outliers)} compras atípicas (acima da média + 2 desvios)', 'detalhes': outliers[['Descrição', 'Valor (R$)']].to_dict('records')})

# Comparar com mês anterior
if variacao > 20:
    insights.append({'tipo': '📈 Aumento Significativo', 'mensagem': f'Seus gastos aumentaram {variacao:.1f}% em relação ao mês anterior', 'detalhes': None})
elif variacao < -20:
    insights.append({'tipo': '📉 Economia', 'mensagem': f'Parabéns! Você economizou {abs(variacao):.1f}% em relação ao mês anterior', 'detalhes': None})

if insights:
    for insight in insights:
        with st.expander(f"{insight['tipo']}: {insight['mensagem']}", expanded=True):
            if insight['detalhes']:
                st.dataframe(pd.DataFrame(insight['detalhes']))
else:
    st.info("✅ Nenhum alerta detectado. Seus gastos estão dentro do padrão!")

st.divider()

# ========================================
# 5. ANÁLISE DETALHADA DE TRANSAÇÕES
# ========================================
st.subheader("🔍 Transações Detalhadas")

col1, col2, col3 = st.columns(3)
with col1:
    min_valor = st.number_input("Valor mínimo (R$)", min_value=0.0, value=0.0)
with col2:
    max_valor = st.number_input("Valor máximo (R$)", min_value=0.0, value=float(gastos_positivos['Valor (R$)'].max()))
with col3:
    busca = st.text_input("🔎 Buscar estabelecimento:")

df_transacoes = gastos_positivos.copy()
df_transacoes = df_transacoes[(df_transacoes['Valor (R$)'] >= min_valor) & (df_transacoes['Valor (R$)'] <= max_valor)]
if busca:
    df_transacoes = df_transacoes[df_transacoes['Descrição'].str.contains(busca, case=False, na=False)]

st.dataframe(
    df_transacoes[['Descrição', 'Valor (R$)', 'Categoria'] if 'Categoria' in df_transacoes.columns else ['Descrição', 'Valor (R$)']].sort_values('Valor (R$)', ascending=False)
    .style.format({'Valor (R$)': 'R$ {:,.2f}'}),
    use_container_width=True,
    hide_index=True
)

csv = df_transacoes.to_csv(index=False).encode('utf-8')
st.download_button("📥 Baixar dados filtrados (CSV)", data=csv, file_name=f"transacoes_{fatura_selecionada.replace(' ', '_')}.csv", mime="text/csv")

st.divider()

# ========================================
# 6. AGENTE DE IA LOCAL (100% PYTHON)
# ========================================
st.subheader("🤖 Agente Inteligente (Modo Local)")

pergunta = st.text_input("Pergunte algo sobre seus gastos:")

if pergunta:
    # -------------------
    # Interpretador simples
    # -------------------
    def interpretar_pergunta(pergunta, df_base):
        pergunta = pergunta.lower()
        operacao = None
        filtro_coluna = None
        filtro_valor = None

        # Operação
        if any(p in pergunta for p in ["total", "soma", "quanto gastei"]):
            operacao = "soma"
        elif "média" in pergunta or "media" in pergunta:
            operacao = "media"
        elif "maior" in pergunta:
            operacao = "max"
        elif any(p in pergunta for p in ["quantas", "quantidade", "contagem"]):
            operacao = "contagem"

        # Categoria
        if "categoria" in pergunta and "Categoria" in df_base.columns:
            for cat in df_base["Categoria"].unique():
                if str(cat).lower() in pergunta:
                    filtro_coluna = "Categoria"
                    filtro_valor = cat
                    break

        # Descrição
        for desc in df_base["Descrição"].unique():
            if str(desc).lower() in pergunta:
                filtro_coluna = "Descrição"
                filtro_valor = desc
                break

        return operacao, filtro_coluna, filtro_valor

    # -------------------
    # Executor
    # -------------------
    def consultar_dataframe_local(df_base, operacao, filtro_coluna=None, filtro_valor=None):
        if filtro_coluna and filtro_valor:
            df_base = df_base[df_base[filtro_coluna].str.contains(str(filtro_valor), case=False, na=False)]

        if operacao == "soma":
            return df_base['Valor (R$)'].sum()
        elif operacao == "media":
            return df_base['Valor (R$)'].mean()
        elif operacao == "max":
            return df_base['Valor (R$)'].max()
        elif operacao == "contagem":
            return len(df_base)
        else:
            return None

    # -------------------
    # Gerador de resposta
    # -------------------
    def gerar_resposta(pergunta, resultado, operacao, filtro_valor=None):
        if resultado is None:
            return "Não consegui entender sua pergunta. Tente reformular."
        if operacao == "soma":
            return f"O total gasto foi de R$ {resultado:,.2f}."
        elif operacao == "media":
            return f"A média dos gastos é R$ {resultado:,.2f}."
        elif operacao == "max":
            return f"A maior compra foi de R$ {resultado:,.2f}."
        elif operacao == "contagem":
            return f"Foram encontradas {int(resultado)} transações."

    # -------------------
    # Rodar agente local
    # -------------------
    operacao, filtro_coluna, filtro_valor = interpretar_pergunta(pergunta, gastos_positivos)
    resultado = consultar_dataframe_local(gastos_positivos, operacao, filtro_coluna, filtro_valor)
    resposta = gerar_resposta(pergunta, resultado, operacao, filtro_valor)

    st.success(resposta)
