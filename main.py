import re
import os

def processar_escolas(sql_file="seedSchool.sql", txt_file="escolas.txt"):
    """
    Converte o arquivo seedSchool.sql para escolas.txt
    Formato: total
             id_escola_base_0 lat lon
    """
    print(f"Processando {sql_file} para {txt_file}...")
    
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            conteudo_sql = f.read()
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{sql_file}' não encontrado.")
        return

    # Regex para capturar: Id, Lat e Lon
    # (1, 'Nome', ..., '-9.574873', '-35.655685')
    # Grupo 'id': O primeiro número
    # Grupo 'lat': O penúltimo item (uma string de número)
    # Grupo 'lon': O último item (uma string de número)
    padrao_escola = r'\(\s*(?P<id>\d+)\s*,.+?,\s*(?P<lat>\'-?[0-9\.]+\')\s*,\s*(?P<lon>\'-?[0-9\.]+\')\s*\)'
    
    linhas_txt = []
    
    for match in re.finditer(padrao_escola, conteudo_sql, flags=re.DOTALL):
        try:
            # Pega o ID e subtrai 1
            id_original = int(match.group('id'))
            id_base_0 = id_original - 1
            
            # Pega lat/lon e remove as aspas simples
            lat = match.group('lat').strip("'")
            lon = match.group('lon').strip("'")
            
            linhas_txt.append(f"{id_base_0} {lat} {lon}")
            
        except Exception as e:
            print(f"Aviso: Falha ao processar a linha: {match.group(0)} | Erro: {e}")

    # Escreve o arquivo .txt
    try:
        total_escolas = len(linhas_txt)
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"{total_escolas}\n")  # Linha 1: Contagem total
            f.write("\n".join(linhas_txt)) # Linhas seguintes
            
        print(f"SUCESSO: '{txt_file}' criado com {total_escolas} escolas.")
        
    except Exception as e:
        print(f"ERRO: Falha ao escrever '{txt_file}'. | Erro: {e}")

def processar_salas(sql_file="seedClassRoom.sql", txt_file="salas.txt"):
    """
    Converte o arquivo seedClassRoom.sql para salas.txt
    Formato: total
             id_escola_base_0 id_sala_base_0 id_etapa id_horario vagas
    """
    print(f"\nProcessando {sql_file} para {txt_file}...")
    
    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            conteudo_sql = f.read()
    except FileNotFoundError:
        print(f"ERRO: Arquivo '{sql_file}' não encontrado.")
        return

    # Regex para capturar: SchoolId, Stage, Schedule, MaxCapacity
    # (1, 2, 2, 'B', 16, 2023)
    # Grupo 'school_id': O primeiro número
    # Grupo 'stage': O segundo número
    # Grupo 'schedule': O terceiro número
    # Grupo 'capacity': O quinto número (pulando a string 'Room')
    padrao_sala = r'\(\s*(?P<school_id>\d+)\s*,\s*(?P<stage>\d+)\s*,\s*(?P<schedule>\d+)\s*,\s*\'.*?\'\s*,\s*(?P<capacity>\d+)\s*,\s*\d+\s*\)'
    
    linhas_txt = []
    room_id_counter = 0  # O 'roomid' que você pediu (sequencial)

    for match in re.finditer(padrao_sala, conteudo_sql, flags=re.DOTALL):
        try:
            # Pega o SchoolId e subtrai 1
            school_id_original = int(match.group('school_id'))
            school_id_base_0 = school_id_original - 1
            
            # Pega os outros campos
            stage = match.group('stage')
            schedule = match.group('schedule')
            capacity = match.group('capacity')
            
            # Gera o room_id sequencial em base zero
            room_id_base_0 = room_id_counter
            
            # Formato: schooldid roomid etapaid horario vagas
            linhas_txt.append(f"{school_id_base_0} {room_id_base_0} {stage} {schedule} {capacity}")
            
            room_id_counter += 1 # Incrementa o ID da sala para a próxima linha
            
        except Exception as e:
            print(f"Aviso: Falha ao processar a linha: {match.group(0)} | Erro: {e}")

    # Escreve o arquivo .txt
    try:
        total_salas = len(linhas_txt)
        with open(txt_file, 'w', encoding='utf-8') as f:
            f.write(f"{total_salas}\n")  # Linha 1: Contagem total
            f.write("\n".join(linhas_txt)) # Linhas seguintes
            
        print(f"SUCESSO: '{txt_file}' criado com {total_salas} salas.")
        
    except Exception as e:
        print(f"ERRO: Falha ao escrever '{txt_file}'. | Erro: {e}")

# --- Ponto de Execução Principal ---
if __name__ == "__main__":
    
    # Verifica se os arquivos SQL existem antes de tentar
    if not os.path.exists("seedSchool.sql"):
        print("ERRO: O arquivo 'seedSchool.sql' não foi encontrado.")
        print("Por favor, coloque este script no mesmo diretório dos seus arquivos .sql")
    else:
        processar_escolas()

    if not os.path.exists("seedClassRoom.sql"):
        print("\nERRO: O arquivo 'seedClassRoom.sql' não foi encontrado.")
        print("Por favor, coloque este script no mesmo diretório dos seus arquivos .sql")
    else:
        processar_salas()