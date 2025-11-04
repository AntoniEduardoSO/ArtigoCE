import pandas as pd

# Lê o arquivo salas.txt
with open('salas.txt', 'r') as f:
    linhas = f.readlines()

# Primeira linha é o total de salas (não vamos usar agora)
total_original = int(linhas[0].strip())

# Lê os dados das salas
dados = []
for linha in linhas[1:]:
    valores = list(map(int, linha.strip().split()))
    dados.append(valores)

# Cria DataFrame
df = pd.DataFrame(dados, columns=['id_escola', 'id_sala', 'id_etapa', 'id_horario', 'capacidade'])

# Filtra removendo as salas com id_horario == 2
df_filtrado = df[df['id_horario'] != 2].copy()

# Reajusta os IDs das salas para serem sequenciais novamente
df_filtrado['id_sala'] = range(1, len(df_filtrado) + 1)

# Total de salas após filtro
total_filtrado = len(df_filtrado)

# Gera o arquivo salas-filtradas.txt
with open('salas-filtradas.txt', 'w') as f:
    f.write(f"{total_filtrado}\n")
    for _, row in df_filtrado.iterrows():
        f.write(f"{row['id_escola']} {row['id_sala']} {row['id_etapa']} {row['id_horario']} {row['capacidade']}\n")

# Extrai os IDs únicos das escolas em ordem crescente
escolas_ativas = sorted(df_filtrado['id_escola'].unique())

# Gera o arquivo escolas-ativas.txt
with open('escolas-ativas.txt', 'w') as f:
    for escola in escolas_ativas:
        f.write(f"{escola}\n")

# Exibe estatísticas
print(f"Processamento concluído!")
print(f"\nSalas originais: {total_original}")
print(f"Salas removidas (horário 2): {total_original - total_filtrado}")
print(f"Salas filtradas: {total_filtrado}")
print(f"Escolas ativas: {len(escolas_ativas)}")
print(f"\nArquivos gerados:")
print(f"- salas-filtradas.txt")
print(f"- escolas-ativas.txt")
