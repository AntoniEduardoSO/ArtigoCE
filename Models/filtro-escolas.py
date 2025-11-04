# filtrar_escolas_corrigido.py

def carregar_escolas(arquivo):
    """Lê o arquivo de escolas e retorna {id:int -> linha:str}."""
    escolas = {}
    with open(arquivo, "r", encoding="utf-8") as f:
        linhas = [linha.strip() for linha in f if linha.strip()]
    for linha in linhas[1:]:  # ignora a primeira (contagem)
        partes = linha.split()
        if len(partes) == 3:
            try:
                escolas[int(partes[0])] = linha
            except ValueError:
                pass
    return escolas


def carregar_ativas(arquivo):
    """Lê o arquivo de ativas. Detecta automaticamente se há contagem na primeira linha."""
    with open(arquivo, "r", encoding="utf-8") as f:
        linhas = [linha.strip() for linha in f if linha.strip()]

    # Detecta se a primeira linha é uma contagem (maior que número de linhas restantes)
    try:
        primeiro_valor = int(linhas[0])
        if primeiro_valor == len(linhas) - 1 or primeiro_valor > 1000:
            linhas = linhas[1:]
    except ValueError:
        pass

    ids = set()
    for linha in linhas:
        try:
            ids.add(int(linha))
        except ValueError:
            pass
    return ids


def salvar_filtradas(escolas, ativas, arquivo_saida):
    filtradas = [escolas[i] for i in sorted(ativas) if i in escolas]
    with open(arquivo_saida, "w", encoding="utf-8") as f:
        f.write(f"{len(filtradas)}\n")
        for linha in filtradas:
            f.write(f"{linha}\n")


def main():
    escolas = carregar_escolas("escolas.txt")
    ativas = carregar_ativas("escolas-ativas.txt")
    salvar_filtradas(escolas, ativas, "escolas-filtradas.txt")
    print(f"✅ Gerado 'escolas-filtradas.txt' com {len(ativas)} escolas ativas (de {len(escolas)} totais).")


if __name__ == "__main__":
    main()
