import pandas as pd

# Lê o arquivo Excel sem cabeçalho
# As colunas serão: 0=id_escola, 1=id_etapa, 2=id_horario, 3=id_aluno
df = pd.read_excel('pmf.xlsx', header=None)

# Renomeia as colunas para facilitar o trabalho
df.columns = ['id_escola', 'id_etapa', 'id_horario', 'id_aluno']

# Agrupa alunos por escola, etapa e horário e conta quantos alunos há em cada grupo
agrupamento = df.groupby(['id_escola', 'id_etapa', 'id_horario']).size().reset_index(name='capacidade')

# Adiciona um ID sequencial para cada sala
agrupamento['id_sala'] = range(1, len(agrupamento) + 1)

# Reordena as colunas conforme o formato de saída desejado
resultado = agrupamento[['id_escola', 'id_sala', 'id_etapa', 'id_horario', 'capacidade']]

# Total de salas
total_salas = len(resultado)

# Gera o arquivo TXT
with open('salas.txt', 'w') as f:
    # Escreve o total de salas
    f.write(f"{total_salas}\n")
    
    # Escreve cada linha com os dados separados por espaço
    for _, row in resultado.iterrows():
        f.write(f"{int(row['id_escola'])} {int(row['id_sala'])} {int(row['id_etapa'])} {int(row['id_horario'])} {int(row['capacidade'])}\n")

print(f"Arquivo 'salas.txt' gerado com sucesso!")
print(f"Total de salas: {total_salas}")
print(f"Total de alunos: {resultado['capacidade'].sum()}")