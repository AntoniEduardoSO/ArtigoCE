# Ler o arquivo
with open('salas.txt', 'r') as f:
    linhas = f.readlines()

# Primeira linha é o total
total = linhas[0].strip()

# Demais linhas são os dados das salas
salas = []
for linha in linhas[1:]:
    dados = linha.strip().split()
    salas.append(dados)

# Ordenar por etapa (índice 2) e depois por turno (índice 3)
salas_ordenadas = sorted(salas, key=lambda x: (int(x[2]), int(x[3])))

# Escrever resultado
with open('salas_ordenadas.txt', 'w') as f:
    f.write(total + '\n')
    for sala in salas_ordenadas:
        f.write(' '.join(sala) + '\n')

print("Arquivo ordenado salvo como 'salas_ordenadas.txt'")
print(f"Total de salas: {total}")
print(f"Primeiras 5 salas ordenadas:")
for sala in salas_ordenadas[:5]:
    print(f"Escola: {sala[0]}, Sala: {sala[1]}, Etapa: {sala[2]}, Turno: {sala[3]}, Cap: {sala[4]}")
