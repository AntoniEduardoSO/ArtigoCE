# Ler o arquivo
with open('alunos.txt', 'r') as f:
    linhas = f.readlines()

# Primeira linha é o total
total = linhas[0].strip()

# Demais linhas são os dados dos alunos
alunos = []
for linha in linhas[1:]:
    dados = linha.strip().split('\t')
    # Limpar espaços extras
    dados = [d.strip() for d in dados if d.strip()]
    alunos.append(dados)

# Ordenar por etapa (índice 3) e depois por turno (índice 4)
alunos_ordenados = sorted(alunos, key=lambda x: (int(x[3]), int(x[4])))

# Escrever resultado
with open('arquivo_ordenado.txt', 'w') as f:
    f.write(total + '\n')
    for aluno in alunos_ordenados:
        f.write('\t'.join(aluno) + '\n')

print("Arquivo ordenado salvo como 'arquivo_ordenado.txt'")
print(f"Total de alunos: {total}")
print(f"Primeiros 5 alunos ordenados:")
for aluno in alunos_ordenados[:5]:
    print(f"ID: {aluno[0]}, Etapa: {aluno[3]}, Turno: {aluno[4]}")
