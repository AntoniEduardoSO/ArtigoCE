import random
import math
import time
from collections import Counter
from deap import base, creator, tools, algorithms
import numpy as np

# --- 1. Constantes de Penalidade e Otimização ---
# Penalidades por violação de restrições (Hard Constraints)
PENALTY_MISMATCH = 10**10           # Pior crime: Aluno na etapa/horário errado
PENALTY_UNASSIGNED_SPECIAL = 10**9  # Segundo pior: Aluno especial sem vaga
PENALTY_UNASSIGNED_NORMAL = 10**8   # Terceiro pior: Aluno normal sem vaga
PENALTY_OVERCAPACITY = 10**7        # Quarto pior: Sala superlotada

# (NOVO) Penalidade para otimização de distância (Soft Constraint)
# Queremos que a média seja 1.2km
DISTANCE_TARGET_KM = 1.2
# Penalidade por cada KM acima da meta (ao quadrado, para penalizar mais quem está longe)
PENALTY_DISTANCE_MULTIPLIER = 10000 

# O AG vai usar as N opções mais próximas para criar e mutar
N_CLOSEST_OPTIONS = 50

# --- 2. Funções de Carregamento de Dados ---

def haversine(lat1, lon1, lat2, lon2):
    """Calcula a distância em km entre duas coordenadas lat/lon."""
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1 = math.radians(lat1)
    lat2 = math.radians(lat2)
    a = math.sin(dLat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dLon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def load_alunos(filepath="alunos.txt"):
    """Carrega alunos. Formato: id, lat, lon, etapa, horario, necessidade_especial"""
    alunos = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            f.readline()
            for line_idx, line in enumerate(f):
                parts = line.split()
                if len(parts) >= 6:
                    try:
                        alunos.append({
                            "id": parts[0],
                            "lat": float(parts[1]),
                            "lon": float(parts[2]),
                            "etapa": int(parts[3]),
                            "horario": int(parts[4]),
                            "special": int(parts[5])
                        })
                    except ValueError:
                        print(f"Ignorando linha mal formatada (aluno): {line.strip()} (Linha {line_idx + 2})")
        print(f"Carregados {len(alunos)} alunos.")
    except FileNotFoundError:
        print(f"ERRO: Arquivo de alunos não encontrado em '{filepath}'")
        return None
    return alunos

def load_escolas(filepath="escolas.txt"):
    """Carrega escolas. Retorna dicionário {id_escola: {lat, lon}}."""
    escolas = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            f.readline()
            for line_idx, line in enumerate(f):
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        escolas[int(parts[0])] = {
                            "lat": float(parts[1]),
                            "lon": float(parts[2])
                        }
                    except ValueError:
                        print(f"Ignorando linha mal formatada (escola): {line.strip()} (Linha {line_idx + 2})")
        print(f"Carregadas {len(escolas)} escolas.")
    except FileNotFoundError:
        print(f"ERRO: Arquivo de escolas não encontrado em '{filepath}'")
        return None
    return escolas

def load_salas(filepath="salas.txt"):
    """Carrega salas. Formato: id_escola, id_sala, etapa, horario, vagas"""
    salas = {}
    total_vagas = 0
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            f.readline()
            for line_idx, line in enumerate(f):
                parts = line.split()
                if len(parts) >= 5:
                    try:
                        id_sala = int(parts[1])
                        vagas = int(parts[4])
                        salas[id_sala] = {
                            "escola_id": int(parts[0]),
                            "etapa": int(parts[2]),
                            "horario": int(parts[3]),
                            "vagas": vagas
                        }
                        total_vagas += vagas
                    except ValueError:
                         print(f"Ignorando linha mal formatada (sala): {line.strip()} (Linha {line_idx + 2})")
        print(f"Carregadas {len(salas)} salas, com um total de {total_vagas} vagas.")
    except FileNotFoundError:
        print(f"ERRO: Arquivo de salas não encontrado em '{filepath}'")
        return None
    return salas

def preprocess_aluno_salas_proximas(alunos, escolas, salas):
    """
    Para cada aluno, cria uma lista de salas válidas (mesma etapa E horário)
    ordenadas pela distância.
    """
    if not alunos or not escolas or not salas:
        return None

    print("Iniciando pré-processamento de distâncias...")
    
    escola_map = {}
    for id_sala, sala in salas.items():
        if sala["escola_id"] not in escolas:
            print(f"Alerta: Sala {id_sala} refere-se a uma escola_id {sala['escola_id']} que não existe em escolas.txt. Ignorando sala.")
            continue
            
        key = (sala["escola_id"], sala["etapa"], sala["horario"])
        if key not in escola_map:
            escola_map[key] = []
        escola_map[key].append(id_sala)

    aluno_sala_map = []
    alunos_sem_opcoes = 0
    unfound_combos = Counter()
    
    for aluno in alunos:
        aluno_etapa = aluno["etapa"]
        aluno_horario = aluno["horario"]
        
        salas_validas_com_dist = []
        
        for id_escola, escola in escolas.items():
            key = (id_escola, aluno_etapa, aluno_horario)
            salas_encontradas = escola_map.get(key)
            
            if salas_encontradas:
                dist = haversine(aluno["lat"], aluno["lon"], escola["lat"], escola["lon"])
                for id_sala in salas_encontradas:
                    salas_validas_com_dist.append((id_sala, dist))
        
        salas_validas_com_dist.sort(key=lambda x: x[1])
        
        if not salas_validas_com_dist:
            alunos_sem_opcoes += 1
            unfound_combos[(aluno_etapa, aluno_horario)] += 1
            
        aluno_sala_map.append([id_sala for id_sala, dist in salas_validas_com_dist])

    print(f"Pré-processamento concluído. {alunos_sem_opcoes} alunos não têm NENHUMA sala (etapa/horário).")
    
    if alunos_sem_opcoes > 0:
        print("\n--- DIAGNÓSTICO DE FALHA (Etapa, Horário) ---")
        for (etapa, horario), count in unfound_combos.items():
            print(f"  Combinação (Etapa: {etapa}, Horário: {horario}) não encontrada para {count} alunos.")
        print("  Verifique se o arquivo 'salas.txt' possui salas para estas combinações.\n")

    return aluno_sala_map


# --- 3. Configuração do Algoritmo Evolucionário (DEAP) ---

ALUNOS = load_alunos("Models/alunos.txt")
ESCOLAS = load_escolas("Models/escolas.txt")
SALAS = load_salas("Models/salas.txt")

if not ALUNOS or not ESCOLAS or not SALAS:
    print("Encerrando script devido a erro no carregamento de arquivos.")
    exit()

ALUNO_SALA_MAP = preprocess_aluno_salas_proximas(ALUNOS, ESCOLAS, SALAS)
if not ALUNO_SALA_MAP:
    print("Encerrando script devido a erro no pré-processamento.")
    exit()

UNASSIGNED_ID = -1
N_ALUNOS = len(ALUNOS)

creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", list, fitness=creator.FitnessMin)

toolbox = base.Toolbox()

def create_individual_greedy():
    """
    (MODIFICADO - NOVO) Cria um indivíduo "guloso".
    Sempre aloca o aluno na sala válida MAIS PRÓXIMA.
    """
    individual = []
    for i in range(N_ALUNOS):
        salas_proximas = ALUNO_SALA_MAP[i]
        
        if salas_proximas:
            individual.append(salas_proximas[0]) # Pega o índice 0 (o mais próximo)
        else:
            individual.append(UNASSIGNED_ID)
    return creator.Individual(individual)

# (MODIFICADO) A população inicial será 100% "greedy"
toolbox.register("individual", create_individual_greedy)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

def evaluate(individual):
    """(MODIFICADO) Função de Fitness com penalidade de distância."""
    total_distance = 0
    unassigned_special = 0
    unassigned_normal = 0
    overcapacity_count = 0
    mismatch_count = 0
    penalty_long_distance = 0 # (NOVO)
    
    sala_counts = Counter(individual)

    # 1. Penalidade por Superlotação
    for id_sala, count in sala_counts.items():
        if id_sala == UNASSIGNED_ID or id_sala not in SALAS:
            continue
        vagas = SALAS[id_sala]["vagas"]
        if count > vagas:
            overcapacity_count += (count - vagas)

    # 2. Penalidades de Alocação e Otimização de Distância
    for i in range(N_ALUNOS):
        aluno = ALUNOS[i]
        id_sala = individual[i]
        
        if id_sala == UNASSIGNED_ID or id_sala not in SALAS:
            if aluno['special'] == 1:
                unassigned_special += 1
            else:
                unassigned_normal += 1
            continue
            
        sala = SALAS[id_sala]
        if sala['etapa'] != aluno['etapa'] or sala['horario'] != aluno['horario']:
            mismatch_count += 1
            continue
            
        if sala["escola_id"] not in ESCOLAS:
            mismatch_count += 1
            continue
            
        escola = ESCOLAS[sala["escola_id"]]
        dist = haversine(aluno["lat"], aluno["lon"], escola["lat"], escola["lon"])
        total_distance += dist
        
        # (NOVO) Adiciona a penalidade de distância se ela passar da meta
        if dist > DISTANCE_TARGET_KM:
            # (dist - DISTANCE_TARGET_KM)**2 -> Penaliza exponencialmente
            penalty_long_distance += ((dist - DISTANCE_TARGET_KM)**2) * PENALTY_DISTANCE_MULTIPLIER
            
    # 3. Cálculo Final
    final_score = (mismatch_count * PENALTY_MISMATCH) + \
                  (unassigned_special * PENALTY_UNASSIGNED_SPECIAL) + \
                  (unassigned_normal * PENALTY_UNASSIGNED_NORMAL) + \
                  (overcapacity_count * PENALTY_OVERCAPACITY) + \
                  penalty_long_distance + \
                  total_distance # A distância real ainda é o otimizador base

    return (final_score,)

def custom_mutate(individual, indpb):
    """Mutação customizada: troca por uma das N mais próximas."""
    for i in range(len(individual)):
        if random.random() < indpb:
            salas_proximas = ALUNO_SALA_MAP[i]
            
            if salas_proximas:
                opcoes_limitadas = salas_proximas[:min(N_CLOSEST_OPTIONS, len(salas_proximas))]
                
                if len(opcoes_limitadas) > 1:
                    nova_sala = random.choice(opcoes_limitadas)
                    while nova_sala == individual[i]:
                        nova_sala = random.choice(opcoes_limitadas)
                    individual[i] = nova_sala
                elif len(opcoes_limitadas) == 1:
                    individual[i] = opcoes_limitadas[0]
            
    return individual,

toolbox.register("evaluate", evaluate)
toolbox.register("mate", tools.cxUniform, indpb=0.5) 
toolbox.register("mutate", custom_mutate, indpb=0.02) # (Reduzido) Mutação mais fina
toolbox.register("select", tools.selTournament, tournsize=3)

# --- 4. Execução do Algoritmo ---

def main():
    start_time = time.time()
    
    # (MODIFICADO) Parâmetros do AG para "Consertar" a solução greedy
    MU = 400         # População grande para manter diversidade de soluções
    LAMBDA = 400     # Número de filhos
    NGEN = 300       # Mais gerações para refinar
    CXPB = 0.6       # Prob. Crossover
    MUTPB = 0.4      # (AUMENTADO) Mutação alta é necessária para explorar
                     # as 2ª, 3ª, 4ª escolas mais próximas.
    
    pop = toolbox.population(n=MU)
    hof = tools.HallOfFame(1) 
    
    # Configura as estatísticas (usando numpy para média)
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", lambda x: np.mean([fit[0] for fit in x]))
    stats.register("min", lambda x: np.min([fit[0] for fit in x]))
    stats.register("max", lambda x: np.max([fit[0] for fit in x]))

    print(f"Iniciando evolução (Greedy Start + MuLa) com {MU} pais, {LAMBDA} filhos por {NGEN} gerações...")
    
    # (MODIFICADO) Usa o algoritmo eaMuPlusLambda
    algorithms.eaMuPlusLambda(pop, toolbox, 
                              mu=MU, 
                              lambda_=LAMBDA, 
                              cxpb=CXPB, 
                              mutpb=MUTPB, 
                              ngen=NGEN, 
                              stats=stats,
                              halloffame=hof, 
                              verbose=True)

    end_time = time.time()
    print(f"\nEvolução concluída em {end_time - start_time:.2f} segundos.")
    
    # --- 5. Geração do Arquivo de Saída ---
    
    if not hof:
        print("ERRO: O Hall da Fama está vazio. Nenhuma solução foi encontrada.")
        return

    best_solution = hof[0]
    best_fitness = best_solution.fitness.values[0]
    
    print(f"\nMelhor fitness (Penalidades + Distância): {best_fitness}")
    
    print("Analisando a melhor solução...")
    sala_counts = Counter(best_solution)
    unassigned_special = 0
    unassigned_normal = 0
    overcapacity_count = 0
    mismatch_count = 0
    total_distance = 0
    distancias = []
    
    for id_sala, count in sala_counts.items():
        if id_sala == UNASSIGNED_ID or id_sala not in SALAS:
            continue
        vagas = SALAS[id_sala]["vagas"]
        if count > vagas:
            overcapacity_count += (count - vagas)
            
    for i in range(N_ALUNOS):
        aluno = ALUNOS[i]
        id_sala = best_solution[i]
        
        if id_sala == UNASSIGNED_ID or id_sala not in SALAS:
            if aluno['special'] == 1:
                unassigned_special += 1
            else:
                unassigned_normal += 1
            continue
        
        sala = SALAS[id_sala]
        if sala['etapa'] != aluno['etapa'] or sala['horario'] != aluno['horario']:
            mismatch_count += 1
            continue
            
        if sala["escola_id"] not in ESCOLAS:
            mismatch_count += 1
            continue
            
        escola = ESCOLAS[sala["escola_id"]]
        dist = haversine(aluno["lat"], aluno["lon"], escola["lat"], escola["lon"])
        total_distance += dist
        distancias.append(dist) # Adiciona para calcular a média correta

    print(f"  (ERRO GRAVE) Alunos em etapa/horário errados: {mismatch_count}")
    print(f"  Alunos com Nec. Especial não alocados: {unassigned_special}")
    print(f"  Alunos (normal) não alocados: {unassigned_normal}")
    print(f"  Vagas excedidas (total): {overcapacity_count}")
    print(f"  Distância total (Km): {total_distance:.2f}")
    
    if distancias:
        print(f"  Distância Média (Km): {np.mean(distancias):.2f}")
        print(f"  Distância Mediana (Km): {np.median(distancias):.2f}")
        print(f"  Distância Máxima (Km): {np.max(distancias):.2f}")
        print(f"  Alunos acima de {DISTANCE_TARGET_KM} Km: {sum(1 for d in distancias if d > DISTANCE_TARGET_KM)}")
    
    
    output_file = "alocacao_final.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("id_aluno;necessidade_especial;id_escola_alocada;id_sala_alocada;etapa_desejada;etapa_sala;horario_desejado;horario_sala\n")
        for i in range(N_ALUNOS):
            aluno = ALUNOS[i]
            id_sala = best_solution[i]
            
            if id_sala == UNASSIGNED_ID or id_sala not in SALAS:
                f.write(f"{aluno['id']};{aluno['special']};NAO_ALOCADO;NAO_ALOCADO;{aluno['etapa']};N/A;{aluno['horario']};N/A\n")
            else:
                sala = SALAS[id_sala]
                id_escola = sala["escola_id"]
                etapa_sala_str = sala['etapa']
                horario_sala_str = sala['horario']
                
                if sala['etapa'] != aluno['etapa'] or sala['horario'] != aluno['horario']:
                    etapa_sala_str = f"ERRADO:{sala['etapa']}"
                    horario_sala_str = f"ERRADO:{sala['horario']}"

                f.write(f"{aluno['id']};{aluno['special']};{id_escola};{id_sala};{aluno['etapa']};{etapa_sala_str};{aluno['horario']};{horario_sala_str}\n")

    print(f"\nArquivo de alocação salvo em: {output_file}")

if __name__ == "__main__":
    # (Adicionado) Import numpy no início do script
    main()