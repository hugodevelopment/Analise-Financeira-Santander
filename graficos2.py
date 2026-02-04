import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import numpy as np

# Configuração da página
st.set_page_config(page_title="Dashboard Cartão", layout="wide", page_icon="💳")

# --- Carregar dados ---
df = pd.read_csv("gastos_consolidados_final.csv")

# Converter data se necessário
if 'Data' in df.columns:
    df['Data'] = pd.to_datetime(df['Data'], errors='coerce')
    df['Mes'] = df['Data'].dt.to_period('M').astype(str)
    df['Dia_Semana'] = df['Data'].dt.day_name()
st.title("💳 Dashboard Inteligente de Gastos do Cartão")

# --- Filtros ---
col1, col2 = st.columns(2)
with col1:
    opcoes = ["Resumo Total"] + sorted(df['Arquivo'].dropna().unique().tolist())
    fatura_selecionada = st.selectbox("📅 Selecione a fatura:", opcoes)

with col2:
    # Filtro de categoria (se tiver)
    if 'Categoria' in df.columns:
        categorias = ["Todas"] + sorted(df['Categoria'].dropna().unique().tolist())
        categoria_selecionada = st.selectbox("🏷️ Categoria:", categorias)
    else:
        categoria_selecionada = "Todas"

# --- Definir base filtrada ---
if fatura_selecionada == "Resumo Total":
    df_filtrado = df.copy()
else:
    df_filtrado = df[df['Arquivo'] == fatura_selecionada]

if categoria_selecionada != "Todas" and 'Categoria' in df.columns:
    df_filtrado = df_filtrado[df_filtrado['Categoria'] == categoria_selecionada]

# ========================================
# 1. CARDS DE KPIs PRINCIPAIS (TOPO)
# ========================================
st.subheader("📊 Visão Geral")

# Calcular métricas
gastos_positivos = df_filtrado[df_filtrado['Valor (R$)'] > 0]
total_gasto = gastos_positivos['Valor (R$)'].sum()
qtd_transacoes = len(gastos_positivos)
ticket_medio = total_gasto / qtd_transacoes if qtd_transacoes > 0 else 0
maior_compra = gastos_positivos['Valor (R$)'].max() if len(gastos_positivos) > 0 else 0

# Comparação com mês anterior (se possível)
if fatura_selecionada != "Resumo Total" and len(opcoes) > 2:
    idx_atual = opcoes.index(fatura_selecionada)
    if idx_atual > 1:  # Tem mês anterior
        fatura_anterior = opcoes[idx_atual - 1]
        df_anterior = df[df['Arquivo'] == fatura_anterior]
        total_anterior = df_anterior[df_anterior['Valor (R$)'] > 0]['Valor (R$)'].sum()
        variacao = ((total_gasto - total_anterior) / total_anterior * 100) if total_anterior > 0 else 0
    else:
        variacao = 0
else:
    variacao = 0

# Cards em colunas
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="💰 Total Gasto",
        value=f"R$ {total_gasto:,.2f}",
        delta=f"{variacao:+.1f}%" if variacao != 0 else None
    )

with col2:
    st.metric(
        label="🛒 Transações",
        value=f"{qtd_transacoes}",
        delta=None
    )

with col3:
    st.metric(
        label="📊 Ticket Médio",
        value=f"R$ {ticket_medio:,.2f}",
        delta=None
    )

with col4:
    st.metric(
        label="🔝 Maior Compra",
        value=f"R$ {maior_compra:,.2f}",
        delta=None
    )

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
        
        fig = px.bar(freq_dia, x='Dia_PT', y='sum', 
                     labels={'sum': 'Total (R$)', 'Dia_PT': 'Dia da Semana'},
                     color='sum', color_continuous_scale='Blues')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Adicione uma coluna 'Data' para ver esta análise")

with col2:
    st.subheader("🏪 Top 5 Estabelecimentos")
    top_estab = gastos_positivos.groupby('Descrição')['Valor (R$)'].sum().reset_index()
    top_estab['%_TOTAL'] = (top_estab['Valor (R$)'] / total_gasto) * 100
    top_estab = top_estab.sort_values(by='Valor (R$)', ascending=False).head(5)
    
    fig = px.bar(top_estab, x='Valor (R$)', y='Descrição', 
                 orientation='h',
                 text='%_TOTAL',
                 labels={'Valor (R$)': 'Total Gasto', 'Descrição': 'Estabelecimento'})
    fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
    st.plotly_chart(fig, use_container_width=True)

st.divider()



# ========================================
# 4. EVOLUÇÃO TEMPORAL E TENDÊNCIAS
# ========================================
st.subheader("📈 Evolução e Tendências")

if fatura_selecionada == "Resumo Total":
    # Análise temporal
    evolucao = df[df['Valor (R$)'] > 0].groupby('Arquivo').agg({
        'Valor (R$)': ['sum', 'count', 'mean']
    }).reset_index()
    evolucao.columns = ['Fatura', 'Total', 'Qtd', 'Ticket_Medio']
    evolucao['Variacao_%'] = evolucao['Total'].pct_change() * 100
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de linha com área
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=evolucao['Fatura'], 
            y=evolucao['Total'],
            mode='lines+markers',
            name='Total Gasto',
            fill='tozeroy',
            line=dict(color='#1f77b4', width=3)
        ))
        fig.update_layout(
            title='Evolução dos Gastos Mensais',
            xaxis_title='Mês',
            yaxis_title='Total (R$)',
            hovermode='x unified'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Média móvel e tendência
        evolucao['Media_Movel_3'] = evolucao['Total'].rolling(window=3, min_periods=1).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=evolucao['Fatura'],
            y=evolucao['Total'],
            name='Gasto Mensal',
            marker_color='lightblue'
        ))
        fig.add_trace(go.Scatter(
            x=evolucao['Fatura'],
            y=evolucao['Media_Movel_3'],
            name='Média Móvel (3 meses)',
            line=dict(color='red', width=2, dash='dash')
        ))
        fig.update_layout(
            title='Gastos vs Média Móvel',
            xaxis_title='Mês',
            yaxis_title='Valor (R$)'
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Tabela de evolução
    st.dataframe(
        evolucao.style.format({
            'Total': 'R$ {:,.2f}',
            'Ticket_Medio': 'R$ {:,.2f}',
            'Variacao_%': '{:+.1f}%'
        }).background_gradient(subset=['Variacao_%'], cmap='RdYlGn', vmin=-20, vmax=20),
        use_container_width=True,
        hide_index=True
    )

st.divider()

# ========================================
# 5. ALERTAS E INSIGHTS INTELIGENTES
# ========================================
st.subheader("🚨 Alertas e Insights")

insights = []

# Detectar gastos atípicos
if len(gastos_positivos) > 0:
    media = gastos_positivos['Valor (R$)'].mean()
    desvio = gastos_positivos['Valor (R$)'].std()
    outliers = gastos_positivos[gastos_positivos['Valor (R$)'] > (media + 2 * desvio)]
    
    if len(outliers) > 0:
        insights.append({
            'tipo': '⚠️ Atenção',
            'mensagem': f'Detectadas {len(outliers)} compras atípicas (acima da média + 2 desvios)',
            'detalhes': outliers[['Descrição', 'Valor (R$)']].to_dict('records')
        })

# Comparar com mês anterior
if variacao > 20:
    insights.append({
        'tipo': '📈 Aumento Significativo',
        'mensagem': f'Seus gastos aumentaram {variacao:.1f}% em relação ao mês anterior',
        'detalhes': None
    })
elif variacao < -20:
    insights.append({
        'tipo': '📉 Economia',
        'mensagem': f'Parabéns! Você economizou {abs(variacao):.1f}% em relação ao mês anterior',
        'detalhes': None
    })

# Categoria com maior crescimento
if fatura_selecionada == "Resumo Total" and 'Categoria' in df.columns:
    for cat in df['Categoria'].unique():
        cat_atual = df_filtrado[df_filtrado['Categoria'] == cat]['Valor (R$)'].sum()
        if idx_atual > 1:
            cat_anterior = df_anterior[df_anterior['Categoria'] == cat]['Valor (R$)'].sum()
            if cat_anterior > 0:
                var_cat = ((cat_atual - cat_anterior) / cat_anterior) * 100
                if var_cat > 50:
                    insights.append({
                        'tipo': '🔥 Categoria em Alta',
                        'mensagem': f'Gastos com "{cat}" aumentaram {var_cat:.1f}%',
                        'detalhes': None
                    })

# Exibir insights
if insights:
    for insight in insights:
        with st.expander(f"{insight['tipo']}: {insight['mensagem']}", expanded=True):
            if insight['detalhes']:
                st.dataframe(pd.DataFrame(insight['detalhes']))
else:
    st.info("✅ Nenhum alerta detectado. Seus gastos estão dentro do padrão!")

st.divider()

# ========================================
# 6. PROJEÇÕES E METAS
# ========================================
st.subheader("🎯 Metas e Projeções")

col1, col2 = st.columns(2)

with col1:
    # Definir meta mensal
    meta_mensal = st.number_input(
        "💰 Defina sua meta de gastos mensal (R$):",
        min_value=0.0,
        value=5000.0,
        step=100.0
    )
    
    percentual_gasto = (total_gasto / meta_mensal * 100) if meta_mensal > 0 else 0
    
    # Gráfico de progresso
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=total_gasto,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': "Gasto Atual vs Meta"},
        delta={'reference': meta_mensal},
        gauge={
            'axis': {'range': [None, meta_mensal * 1.2]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, meta_mensal * 0.7], 'color': "lightgreen"},
                {'range': [meta_mensal * 0.7, meta_mensal], 'color': "yellow"},
                {'range': [meta_mensal, meta_mensal * 1.2], 'color': "red"}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': meta_mensal
            }
        }
    ))
    st.plotly_chart(fig, use_container_width=True)
    
    if percentual_gasto > 100:
        st.error(f"⚠️ Você ultrapassou sua meta em {percentual_gasto - 100:.1f}%!")
    elif percentual_gasto > 80:
        st.warning(f"⚠️ Atenção! Você já gastou {percentual_gasto:.1f}% da sua meta.")
    else:
        st.success(f"✅ Você gastou {percentual_gasto:.1f}% da sua meta. Continue assim!")

with col2:
    # Projeção para final do mês
    if 'Data' in df_filtrado.columns and len(df_filtrado) > 0:
        dias_decorridos = df_filtrado['Data'].dt.day.max()
        dias_mes = 30  # Simplificação
        
        if dias_decorridos > 0:
            gasto_diario_medio = total_gasto / dias_decorridos
            projecao_mes = gasto_diario_medio * dias_mes
            
            st.metric(
                label="📊 Projeção para o Mês",
                value=f"R$ {projecao_mes:,.2f}",
                delta=f"{((projecao_mes - meta_mensal) / meta_mensal * 100):+.1f}% vs Meta"
            )
            
            st.metric(
                label="📅 Gasto Médio Diário",
                value=f"R$ {gasto_diario_medio:,.2f}"
            )
            
            # Recomendação
            dias_restantes = dias_mes - dias_decorridos
            saldo_disponivel = meta_mensal - total_gasto
            gasto_diario_recomendado = saldo_disponivel / dias_restantes if dias_restantes > 0 else 0
            
            if gasto_diario_recomendado > 0:
                st.info(f"💡 Para não estourar a meta, gaste no máximo R$ {gasto_diario_recomendado:.2f}/dia nos próximos {dias_restantes} dias.")
            else:
                st.warning(f"⚠️ Meta já ultrapassada! Tente economizar R$ {abs(gasto_diario_recomendado):.2f}/dia.")

st.divider()

# ========================================
# 7. ANÁLISE DETALHADA DE TRANSAÇÕES
# ========================================
st.subheader("🔍 Transações Detalhadas")

# Filtros adicionais
col1, col2, col3 = st.columns(3)
with col1:
    min_valor = st.number_input("Valor mínimo (R$)", min_value=0.0, value=0.0)
with col2:
    max_valor = st.number_input("Valor máximo (R$)", min_value=0.0, value=float(gastos_positivos['Valor (R$)'].max()))
with col3:
    busca = st.text_input("🔎 Buscar estabelecimento:")

# Aplicar filtros
df_transacoes = gastos_positivos.copy()
df_transacoes = df_transacoes[
    (df_transacoes['Valor (R$)'] >= min_valor) &
    (df_transacoes['Valor (R$)'] <= max_valor)
]

if busca:
    df_transacoes = df_transacoes[
        df_transacoes['Descrição'].str.contains(busca, case=False, na=False)
    ]

# Exibir tabela
st.dataframe(
    df_transacoes[['Descrição', 'Valor (R$)', 'Categoria'] if 'Categoria' in df_transacoes.columns else ['Descrição', 'Valor (R$)']]
    .sort_values('Valor (R$)', ascending=False)
    .style.format({'Valor (R$)': 'R$ {:,.2f}'}),
    use_container_width=True,
    hide_index=True
)

# Botão de download
csv = df_transacoes.to_csv(index=False).encode('utf-8')
st.download_button(
    label="📥 Baixar dados filtrados (CSV)",
    data=csv,
    file_name=f"transacoes_{fatura_selecionada.replace(' ', '_')}.csv",
    mime="text/csv"
)