# filtrar_alunos.py

def main():
    arquivo_entrada = "alunos.txt"
    arquivo_saida = "alunos-filtrados.txt"

    removidos = 0
    linhas_filtradas = []

    with open(arquivo_entrada, "r", encoding="utf-8") as f:
        for linha in f:
            linha_limpa = linha.strip()
            if not linha_limpa:
                continue  # pula linhas vazias

            partes = linha_limpa.split()
            # Garante que há pelo menos 5 colunas antes de acessar a 5ª
            if len(partes) >= 5 and partes[4] == "2":
                removidos += 1
                continue  # ignora essa linha
            linhas_filtradas.append(linha_limpa)

    with open(arquivo_saida, "w", encoding="utf-8") as f:
        for linha in linhas_filtradas:
            f.write(linha + "\n")

    print(f"✅ {removidos} alunos removidos.")
    print(f"📄 Arquivo gerado: {arquivo_saida}")


if __name__ == "__main__":
    main()
