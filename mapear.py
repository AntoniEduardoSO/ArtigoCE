import re

# --- Arquivos de entrada e saída (Verifique se 'seedSchool (1).sql' está correto) ---
ESCOLAS_IN = 'seedSchool.sql'
SALAS_IN = 'seedClassRoom.sql'
ESCOLAS_OUT = 'seedSchool_sequencial.sql'
SALAS_OUT = 'seedClassRoom_sequencial.sql'

# --- 1. FUNÇÃO DE EXTRAÇÃO DE DADOS BRUTOS (Para mapeamento) ---
def extrair_ids_e_mapa(filename):
    """Lê o arquivo de escolas para criar o mapa de ID_Original -> ID_Sequencial."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{filename}' não encontrado.")
        return {}, None

    # Regex para encontrar o bloco VALUES(...)
    match = re.search(r'VALUES\s*\((.*)\);', content, re.DOTALL)
    if not match:
        print(f"AVISO: Não foi encontrado o bloco VALUES no arquivo '{filename}'.")
        # Tentativa de fallback: buscar IDs em todo o arquivo
        ids_originais = re.findall(r'\(\s*(\d+)\s*,', content)
    else:
        raw_values_block = match.group(1).strip()
        # Regex mais segura: Captura o número inteiro logo após o parêntese de abertura e antes da primeira vírgula.
        ids_originais = re.findall(r'\(\s*(\d+)\s*,', raw_values_block)
    
    id_map = {}
    if not ids_originais:
        print("ERRO FATAL: Não foi possível extrair IDs de Escola. Verifique o formato do SQL.")
        return {}, content # Retorna o conteúdo para tentar o mapeamento mesmo assim

    for idx, id_str in enumerate(ids_originais):
        try:
            id_original = int(id_str)
            id_sequencial = idx # 1 -> 0, 2 -> 1, 3 -> 2, etc.
            id_map[id_original] = id_sequencial
        except ValueError:
            continue
    
    # Se o ID mais alto encontrado for 151, a contagem está correta.
    print(f"INFO: Mapeadas {len(id_map)} escolas (IDs originais de {min(id_map.keys())} a {max(id_map.keys())}).")
    return id_map, content

# --- 2. FUNÇÃO PARA APLICAR O MAPEAR E GERAR NOVOS ARQUIVOS ---
def aplicar_mapeamento_sql(content, id_map, output_filename, is_schools_file=False):
    """
    Substitui o primeiro ID de cada tupla, garantindo a preservação da sintaxe SQL: (ID, ...
    """
    
    def replace_id_sequencial(match):
        # match.group(1) = '('
        # match.group(2) = ID original (e.g., '1')
        # match.group(3) = ','
        
        id_original = int(match.group(2))
        id_sequencial = id_map.get(id_original)
        
        # Se por algum motivo o ID original não estiver no mapa, não substitui (isso é um erro)
        if id_sequencial is None:
             print(f"AVISO: ID de escola {id_original} não encontrado no mapa.")
             return match.group(0) # Retorna a string original

        # Retorna o parêntese de abertura + o novo ID sequencial + a vírgula
        return f"{match.group(1)}{id_sequencial}{match.group(3)}"

    # O padrão é o mesmo para ambos os arquivos: achar a sequência (ID_NUMERO,
    # Captura 1: '(' | Captura 2: ID_NUMERO | Captura 3: ','
    pattern = re.compile(r'(\()\s*(\d+)\s*(,)', re.DOTALL) 
    
    new_content = pattern.sub(replace_id_sequencial, content)
    
    with open(output_filename, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print(f"✅ Arquivo SQL ajustado salvo como '{output_filename}'.")
    return new_content 

# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    print("--- INICIANDO MAPEAMENTO DE ID (1-151 -> 0-150) E CORREÇÃO DE SINTAXE SQL ---")
    
    # 1. Cria o mapa de ID e carrega o conteúdo original das escolas
    id_map, escolas_content = extrair_ids_e_mapa(ESCOLAS_IN)
    
    if not id_map:
        print("Falha ao criar o mapa de IDs. Abortando o mapeamento.")
    else:
        # 2. Gera o novo arquivo de escolas com IDs sequenciais
        aplicar_mapeamento_sql(escolas_content, id_map, ESCOLAS_OUT, is_schools_file=True)
        
        # 3. Carrega e gera o novo arquivo de salas com SchoolId sequenciais
        try:
            with open(SALAS_IN, 'r', encoding='utf-8') as f:
                salas_content = f.read()
            aplicar_mapeamento_sql(salas_content, id_map, SALAS_OUT)
        except FileNotFoundError:
            print(f"ERRO: Arquivo '{SALAS_IN}' não encontrado. O mapeamento do Classroom não foi realizado.")
            
        print("\n--- MAPEAMENTO SQL CONCLUÍDO. USE OS ARQUIVOS *_sequencial.sql NO SCRIPT DE CONVERSÃO ---")