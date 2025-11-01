import re

# --- Arquivos de entrada e saída ---
ESCOLAS_SQL = 'seedSchool_sequencial.sql'
SALAS_SQL = 'seedClassRoom_sequencial.sql'
ESCOLAS_OUT = 'escolas.txt'
SALAS_OUT = 'salas.txt'

def extrair_valores_sql(filename):
    """
    Lê o conteúdo do arquivo SQL e extrai tuplas de valores, tratando
    vírgulas dentro de strings e garantindo a separação correta de tuplas.
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{filename}' não encontrado.")
        return []

    # 1. Encontrar o bloco VALUES(...)
    match = re.search(r'VALUES\s*\((.*)\);', content, re.DOTALL)
    if not match:
        print(f"AVISO: Não foi encontrado o bloco VALUES no arquivo '{filename}'.")
        return []
    
    raw_values_block = match.group(1).strip()
    
    # 2. Dividir em tuplas individuais. O padrão é que cada tupla começa com '(' e termina com '),'.
    # Usamos uma regex para encontrar todas as ocorrências de tuplas (exceto a primeira/última, 
    # que são tratadas pelo bloco).
    
    # Esta regex localiza o conteúdo de cada parênteses:
    # Captura tudo dentro de ( ... ) que não seja um parêntese, exceto o final.
    # Ex: (VALOR1, 'STRING, COM VÍRGULA', VALOR3)
    
    # Expressão ajustada para garantir a captura das 151 tuplas:
    tuplas_raw = re.findall(r'\((.*?)\)(?:,\s*|\s*$)', raw_values_block, re.DOTALL)
    
    if not tuplas_raw:
        # Tenta uma abordagem mais simples se a regex complexa falhar na primeira tupla
        tuplas_raw = raw_values_block.split('), (')
        tuplas_raw = [t.strip('()') for t in tuplas_raw]
    
    tuples = []
    
    for raw_tuple in tuplas_raw:
        # Usa shlex para dividir a string de forma segura, respeitando strings entre aspas
        # (shlex não é nativo para este uso, então vamos usar uma função de split baseada em regex que respeita as aspas)

        # Regex para dividir por vírgula que NÃO está dentro de aspas simples
        items = re.split(r",\s*(?=(?:[^']*'[^']*')*[^']*$)", raw_tuple)
        
        cleaned_items = []
        for item in items:
            # Remove as aspas simples e limpa espaços
            # Mantém os dados numéricos (Lat/Lon) como estão, mas remove aspas de strings
            cleaned_items.append(item.strip().strip("'").strip())
            
        if cleaned_items and cleaned_items[0]: # Ignora tuplas vazias
            tuples.append(cleaned_items)
        
    return tuples

# --- 2. GERAÇÃO DO ARQUIVO DE ESCOLAS ---
def gerar_escolas_txt(escolas_data):
    # Dicionário para mapear ID original da escola para o novo ID sequencial
    id_map = {}
    escolas_list = []

    # O formato da query de escola é:
    # (Id, Name, Email, PhoneNumber, Ra, Neighborhood, Address, Lat, Lon)
    # Índices relevantes (0-based): Id=0, Lat=7, Lon=8
    
    for idx, data in enumerate(escolas_data):
        try:
            id_original = int(data[0])
            lat = float(data[7])
            lon = float(data[8])
        except (ValueError, IndexError) as e:
            print(f"ERRO ao processar escola na linha {idx+1}. Ignorando. Detalhe: {e}")
            continue

        id_map[id_original] = idx # Mapeia ID original -> ID Sequencial (índice)
        escolas_list.append((idx, lat, lon))

    # Escreve o arquivo de saída
    with open(ESCOLAS_OUT, 'w', encoding='utf-8') as f:
        f.write(f"{len(escolas_list)}\n")
        for id_seq, lat, lon in escolas_list:
            # Formato esperado: id_escola_sequencial lat lon
            f.write(f"{id_seq} {lat:.6f} {lon:.6f}\n")
            
    print(f"✅ Arquivo '{ESCOLAS_OUT}' gerado com {len(escolas_list)} registros.")
    return id_map

# --- 3. GERAÇÃO DO ARQUIVO DE SALAS ---
def gerar_salas_txt(salas_data, escola_id_map):
    salas_list = []
    
    # O formato da query de salas (SchoolClassRoom) é:
    # (SchoolId, Stage, Schedule, Room, MaxCapacity, Year)
    # Índices relevantes (0-based): SchoolId=0, Stage=1, MaxCapacity=4
    
    id_sala_sequencial = 0
    for idx, data in enumerate(salas_data):
        try:
            id_escola_original = int(data[0])
            id_etapa = int(data[1])
            capacidade = int(data[4])
        except (ValueError, IndexError) as e:
            print(f"ERRO ao processar sala na linha {idx+1}. Ignorando. Detalhe: {e}")
            continue

        # Verifica se a escola existe no mapa (e se foi processada corretamente)
        if id_escola_original not in escola_id_map:
            print(f"AVISO: Sala {id_sala_sequencial} referencia ID de Escola {id_escola_original} desconhecido. Ignorando.")
            continue
            
        id_escola_sequencial = escola_id_map[id_escola_original]
        
        salas_list.append((id_sala_sequencial, id_etapa, capacidade))
        id_sala_sequencial += 1


    # Escreve o arquivo de saída
    with open(SALAS_OUT, 'w', encoding='utf-8') as f:
        f.write(f"{len(salas_list)}\n")
        for id_sala, (id_escola_seq, id_etapa, capacidade) in enumerate(salas_list):
            # Formato esperado: id_sala_sequencial id_escola_sequencial id_etapa capacidade
            f.write(f"{id_sala} {id_escola_seq} {id_etapa} {capacidade}\n")
            
    print(f"✅ Arquivo '{SALAS_OUT}' gerado com {len(salas_list)} registros.")
    
# --- EXECUÇÃO PRINCIPAL ---
if __name__ == "__main__":
    print("--- INICIANDO CONVERSÃO SQL PARA TXT ---")
    
    # 1. Extrai e gera escolas.txt (Cria o mapa de IDs)
    escolas_data = extrair_valores_sql(ESCOLAS_SQL)
    if not escolas_data:
        print("Falha na extração dos dados das escolas. Abortando.")
    else:
        escola_id_map = gerar_escolas_txt(escolas_data)
        
        # 2. Extrai e gera salas.txt (Usa o mapa de IDs)
        salas_data = extrair_valores_sql(SALAS_SQL)
        if not salas_data:
            print("Falha na extração dos dados das salas. Conversão incompleta.")
        else:
            gerar_salas_txt(salas_data, escola_id_map)
            
    print("--- CONVERSÃO CONCLUÍDA ---")