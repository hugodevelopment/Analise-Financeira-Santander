import pandas as pd
import numpy as np
from pathlib import Path

# --- CONFIGURAÇÃO ---
COLUNA_DATA = 'Data' 
ARQUIVO_ENTRADA = "gastos_consolidados.csv" # Usando o arquivo que você subiu
ARQUIVO_SAIDA = 'gastos_consolidados_final.csv' 

def apply_transformations_intervalos(df_consolidado, coluna_data):
    """
    Aplica as transformações MES_FATURA e SEMANA_FATURA usando a lógica de 
    intervalos explícitos (17 a 16) e mapeamento condicional.
    """
    df = df_consolidado.copy()
    
    # Adicionar o ano ao formato da data (10/02 vira 10/02/2025)
    #df[coluna_data] = df[coluna_data].astype(str) + '/2025'

    mask_sem_ano = df[coluna_data].str.match(r'^\d{1,2}/\d{1,2}$', na=False)

# Regra: se o arquivo for 'fatura-jan.pdf' → concatena 2024, senão concatena 2025
    df.loc[mask_sem_ano, coluna_data] = np.where(
    df.loc[mask_sem_ano, 'Arquivo'].str.contains('fatura-jan', case=False),
    df.loc[mask_sem_ano, coluna_data] + '/2024',
    df.loc[mask_sem_ano, coluna_data] + '/2025'
)


    print(df[coluna_data].head())
    
   # Agora converter para datetime com formato correto
    df[coluna_data] = pd.to_datetime(df[coluna_data], format='%d/%m/%Y', utc=True, errors='coerce')

    print(df[coluna_data].dtype)

    print(f"   - Coluna '{coluna_data}' convertida para datetime com sucesso.")
    #print(f"   - Total de datas inválidas: {df[coluna_data].isna().sum()}")
    
    print("Iniciando Transformações com Lógica de Fatura por Intervalos Explícitos...")

    # =================================================================
    # 2. CRIAÇÃO da coluna MES_FATURA (Lógica de Intervalos Explícitos)
    # =================================================================
    
    # 2.1. Definir os intervalos de data e o nome da Fatura correspondente
    # Fatura de FEVEREIRO = Gastos de 17/Jan a 16/Fev
    # Fatura de MARÇO = Gastos de 17/Fev a 16/Mar
    
    # Lista das datas de início do ciclo (dia 17)
    start_dates = pd.to_datetime([
        '2024-12-04', '2025-01-04', '2025-02-04', '2025-03-04',
        '2025-05-04', '2025-06-04', '2025-07-04', '2025-08-04', 
        '2025-09-04', '2025-10-04', '2025-11-04'
    ], utc=True)
    
    # Lista das datas de fim do ciclo (dia 16 do mês seguinte)
    # O final é sempre o dia 16 do mês da fatura.
    end_dates = pd.to_datetime([
        '2025-01-03', '2025-02-03', '2025-03-03', '2025-04-03', 
        '2025-06-03', '2025-07-03', '2025-08-03', '2025-09-03', 
        '2025-10-03', '2025-11-03', '2025-12-03' # Assumindo análise até Nov/2025
    ], utc=True)
    
    # Lista dos rótulos de fatura
    rotulos_fatura = [
        '2025-01 (JAN)', '2025-02 (FEV)', '2025-03 (MAR)', '2025-04 (ABR)', '2025-05 (MAI)', 
        '2025-06 (JUN)', '2025-07 (JUL)', '2025-08 (AGO)', '2025-09 (SET)', 
        '2025-10 (OUT)', '2025-11 (NOV)'
    ]
    
    # 2.2. Criar as condições e aplicar o mapeamento
    condicoes = []
    
    # Cria as condições (Inicio_Ciclo <= data <= Fim_Ciclo)
    for start, end in zip(start_dates, end_dates):
        condicoes.append((df[coluna_data] >= start) & (df[coluna_data] <= end))
        print(f"   - Condição criada: {condicoes[-1]} para intervalo {start.date()} a {end.date()}")

    # Aplica o mapeamento vetorizado
    df['MES_FATURA'] = np.select(condicoes, rotulos_fatura)
    
    print("   - Coluna 'MES_FATURA' mapeada com sucesso usando intervalos explícitos.")
    
    # =================================================================
    # 3. CRIAÇÃO da coluna SEMANA_FATURA (Mapeamento Direto para o Ciclo)
    # Reutilizando a lógica condicional simples e eficiente
    # =================================================================
    
    dia = df[coluna_data].dt.day

    # Definir as Condições (baseado nos intervalos de dias do mês civil)
    condicoes_semana = [
        (dia >= 1) & (dia <= 8),  # Semana 1: Início do Ciclo (17 a 23)
        (dia >= 9) & (dia <= 16),  # Semana 2: Meio do Ciclo (24 a 31)
        (dia >= 17) & (dia <= 23),   # Semana 3: Meio do Ciclo (01 a 07)
        (dia >= 24) & (dia <= 31)   # Semana 4: Perto do Corte (08 a 16)
    ]

    # Definir os Valores de Retorno
    valores_semana = [1, 2, 3, 4]

    # Aplicar o mapeamento de forma vetorizada
    df['SEMANA_FATURA'] = np.select(condicoes_semana, valores_semana, default=0)
    
    print("   - Coluna 'SEMANA_FATURA' mapeada com sucesso (1 = Início do Ciclo).")

    # =================================================================
    # 4. CARREGAMENTO
    # =================================================================
    
    # Colunas finais para exportação
    cols_finais = ['MES_FATURA', 'SEMANA_FATURA', coluna_data] + [c for c in df.columns if c not in ['MES_FATURA', 'SEMANA_FATURA', coluna_data]]
    df_exportar = df[cols_finais]

    df_exportar.to_csv(ARQUIVO_SAIDA, index=False, encoding='utf-8')
    
    print(f"\n--- SUCESSO! Arquivo salvo como: {ARQUIVO_SAIDA} ---")
    return df_exportar

# ----------------- INÍCIO DA EXECUÇÃO -----------------

# Carregando o arquivo que você subiu
try:
    df_input = pd.read_csv(ARQUIVO_ENTRADA)
    
    # Execute a função principal
    df_final = apply_transformations_intervalos(df_input, COLUNA_DATA)

    print(df_final)
    
except FileNotFoundError:
    print(f"ERRO: Arquivo de entrada '{ARQUIVO_ENTRADA}' não encontrado.")
    print("Certifique-se de que o arquivo consolidado está no local correto.")