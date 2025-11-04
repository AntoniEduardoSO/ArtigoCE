import random
import math
from collections import Counter, defaultdict
import time
import concurrent.futures

from deap import base, creator, tools, algorithms

# --- Constantes de Penalidade ---
PENALTY_OVERCAPACITY = 10000.0
PENALTY_UNASSIGNED = 1000000.0
UNASSIGNED_SALA_ID = -1

# --- 1. Cálculo de Distância (Haversine) ---
def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    a = math.sin(dLat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dLon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

# --- 2. Funções de Carregamento de Dados ---
def load_escolas(filepath="escolas.txt"):
    escolas = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        f.readline()
        for line in f:
            parts = line.split()
            if len(parts) >= 3:
                escolas[int(parts[0])] = {
                    "lat": float(parts[1]),
                    "lon": float(parts[2])
                }
    print(f"✓ Carregadas {len(escolas)} escolas.")
    return escolas

def load_salas(filepath="salas.txt"):
    salas = {}
    with open(filepath, 'r', encoding='utf-8') as f:
        f.readline()
        for line in f:
            parts = line.split()
            if len(parts) >= 5:
                id_sala = int(parts[1])
                salas[id_sala] = {
                    "escola_id": int(parts[0]),
                    "etapa": int(parts[2]),
                    "horario": int(parts[3]),
                    "vagas": int(parts[4])
                }
    print(f"✓ Carregadas {len(salas)} salas.")
    return salas

def load_and_group_alunos(filepath):
    """
    Carrega TODOS os alunos e os separa em grupos por (etapa, horario).
    Não há mais filtro de etapas.
    """
    alunos_por_grupo = defaultdict(list)
    total_carregados = 0
    with open(filepath, 'r', encoding='utf-8') as f:
        f.readline() # Pula contador
        for line in f:
            parts = line.split()
            if len(parts) >= 6:
                aluno_etapa = int(parts[3])
                aluno_horario = int(parts[4])
                
                # Adiciona o aluno ao seu grupo (etapa, horario)
                alunos_por_grupo[(aluno_etapa, aluno_horario)].append({
                    "id": parts[0],
                    "lat": float(parts[1]),
                    "lon": float(parts[2]),
                    "etapa": aluno_etapa,
                    "horario": aluno_horario,
                    "special": int(parts[5])
                })
                total_carregados += 1
    
    print(f"✓ Carregados {total_carregados} alunos (TODAS AS ETAPAS).")
    print(f"✓ Separados em {len(alunos_por_grupo)} grupos (tarefas).")
    return alunos_por_grupo

def group_salas(salas):
    """Agrupa IDs de salas por (etapa, horario) para consulta rápida."""
    salas_por_grupo = defaultdict(list)
    for id_sala, sala in salas.items():
        if sala["escola_id"] in ESCOLAS: # Valida se escola existe
            salas_por_grupo[(sala["etapa"], sala["horario"])].append(id_sala)
    return salas_por_grupo

# --- 3. Configuração Global DEAP ---
creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", list, fitness=creator.FitnessMin)

# --- 4. Motor da Thread ---

def run_evolution_for_group(task_data):
    """
    Recebe um grupo de alunos, roda um AG completo para eles,
    e retorna a melhor solução encontrada.
    """
    grupo_key, alunos_do_grupo = task_data
    etapa, horario = grupo_key
    n_alunos_grupo = len(alunos_do_grupo)
    
    print(f"  [Thread {etapa}-{horario}] Iniciando. {n_alunos_grupo} alunos...")

    # 1. Pré-processamento LOCAL (só para este grupo)
    ids_salas_do_grupo = SALAS_POR_GRUPO.get(grupo_key, [])
    
    if not ids_salas_do_grupo:
        print(f"  [Thread {etapa}-{horario}] AVISO: Nenhuma sala encontrada. {n_alunos_grupo} alunos não serão alocados.")
        return (grupo_key, [UNASSIGNED_SALA_ID] * n_alunos_grupo, alunos_do_grupo)

    local_aluno_opcoes = []
    local_dist_map = defaultdict(dict)

    for i, aluno in enumerate(alunos_do_grupo):
        opcoes = []
        for id_sala in ids_salas_do_grupo:
            sala = SALAS[id_sala]
            escola = ESCOLAS[sala["escola_id"]]
            dist = haversine(aluno["lat"], aluno["lon"], escola["lat"], escola["lon"])
            opcoes.append((id_sala, dist))
            local_dist_map[i][id_sala] = dist
        opcoes.sort(key=lambda x: x[1])
        local_aluno_opcoes.append(opcoes)

    # 2. Configuração de Toolbox LOCAL (para esta thread)
    toolbox = base.Toolbox()
    
    def create_individual_local():
        ind = []
        for i in range(n_alunos_grupo):
            if local_aluno_opcoes[i]:
                ind.append(local_aluno_opcoes[i][0][0])
            else:
                ind.append(UNASSIGNED_SALA_ID)
        return creator.Individual(ind)

    def evaluate_local(individual):
        total_distance = 0
        penalty = 0
        sala_counts = Counter(individual)
        
        for id_sala, count in sala_counts.items():
            if id_sala == UNASSIGNED_SALA_ID:
                penalty += count * PENALTY_UNASSIGNED
                continue
            vagas = SALAS[id_sala]["vagas"]
            if count > vagas:
                penalty += (count - vagas) * PENALTY_OVERCAPACITY
                
        for i, id_sala in enumerate(individual):
            if id_sala != UNASSIGNED_SALA_ID:
                total_distance += local_dist_map[i][id_sala]
        return (total_distance + penalty,)

    def mutate_local(individual, indpb):
        for i in range(n_alunos_grupo):
            if random.random() < indpb:
                top_opcoes = [s for s,d in local_aluno_opcoes[i][:10]]
                if top_opcoes:
                    individual[i] = random.choice(top_opcoes)
        return individual,

    toolbox.register("individual", create_individual_local)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("evaluate", evaluate_local)
    toolbox.register("mate", tools.cxTwoPoint)
    toolbox.register("mutate", mutate_local, indpb=0.05)
    toolbox.register("select", tools.selTournament, tournsize=3)
    
    # 3. Execução do AG LOCAL
    N_POP_LOCAL = 100
    N_GEN_LOCAL = 50
    
    pop = toolbox.population(n=N_POP_LOCAL)
    hof = tools.HallOfFame(1)
    
    algorithms.eaSimple(pop, toolbox, 
                         cxpb=0.7, mutpb=0.2, ngen=N_GEN_LOCAL, 
                         halloffame=hof, verbose=False)
    
    best_fitness = hof[0].fitness.values[0]
    print(f"  [Thread {etapa}-{horario}] Concluído. Fitness: {best_fitness:.2f}")
    
    return (grupo_key, hof[0], alunos_do_grupo)


# --- 5. Execução Principal (Thread Mestra) ---
if __name__ == "__main__":
    
    print("="*60)
    print("Iniciando Alocador de Alunos (Foco: TODAS AS ETAPAS com Threads)")
    print("="*60)

    start_time_total = time.time()

    # Carrega dados
    ESCOLAS = load_escolas("Models/escolas.txt")
    SALAS = load_salas("Models/salas.txt")
    
    # Agrupa salas globalmente
    SALAS_POR_GRUPO = group_salas(SALAS)
    
    # Carrega TODOS os alunos.
    alunos_por_grupo = load_and_group_alunos("Models/alunos.txt")

    if not alunos_por_grupo:
        print("\n✗ Nenhum aluno encontrado. Encerrando.")
        exit()
        
    tarefas = list(alunos_por_grupo.items())
    
    print(f"\n🚀 Iniciando ThreadPoolExecutor com {len(tarefas)} tarefas (threads)...")
    print(f"   (Isso pode demorar vários minutos, dependendo do n° de grupos)")
    
    resultados_finais = []
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future_to_task = {executor.submit(run_evolution_for_group, task): task for task in tarefas}
        
        for future in concurrent.futures.as_completed(future_to_task):
            try:
                result = future.result()
                resultados_finais.append(result)
            except Exception as e:
                # Mostra qual grupo falhou
                task_key = future_to_task[future][0]
                print(f"  [ERRO GRAVE] Thread {task_key} falhou: {e}")

    print("\n" + "="*60)
    print("Todas as threads concluídas. Consolidando resultados...")
    print("="*60)

    # --- 6. Resultados e Verificação ---
    
    output_filename = "resultado_alocacao.txt"
    total_dist_geral = 0
    total_alunos_geral = 0
    total_nao_alocados = 0
    
    try:
        with open(output_filename, 'w', encoding='utf-8') as f:
            header = f"{'ID Aluno':<10} | {'Etapa':<5} | {'Horario':<7} | {'Lat Aluno':<12} | {'Lon Aluno':<12} | {'-> ID Escola':<12} | {'Lat Escola':<12} | {'Lon Escola':<12} | {'Dist (km)':<10}\n"
            separator = "-" * len(header.strip()) + "\n"
            
            f.write("VERIFICAÇÃO (Aluno LAT/LON -> Escola LAT/LON) - TODAS AS ETAPAS (THREADS)\n")
            f.write(separator)
            f.write(header)
            f.write(separator)

            # Ordena os resultados para o arquivo ficar organizado por etapa/horario
            resultados_finais.sort(key=lambda x: x[0]) # Ordena por (etapa, horario)

            for grupo_key, best_solution, alunos_do_grupo in resultados_finais:
                etapa, horario = grupo_key
                total_alunos_geral += len(alunos_do_grupo)
                
                for i, id_sala in enumerate(best_solution):
                    aluno = alunos_do_grupo[i]
                    
                    if id_sala == UNASSIGNED_SALA_ID:
                        total_nao_alocados += 1
                        f.write(f"{aluno['id']:<10} | {aluno['etapa']:<5} | {aluno['horario']:<7} | {aluno['lat']:<12.6f} | {aluno['lon']:<12.6f} | {'NAO ALOCADO':<12} | {'-':<12} | {'-':<12} | {'-':<10}\n")
                    else:
                        sala = SALAS[id_sala]
                        escola = ESCOLAS[sala["escola_id"]]
                        dist = haversine(aluno["lat"], aluno["lon"], escola["lat"], escola["lon"])
                        
                        total_dist_geral += dist
                        
                        f.write(f"{aluno['id']:<10} | {aluno['etapa']:<5} | {aluno['horario']:<7} | {aluno['lat']:<12.6f} | {aluno['lon']:<12.6f} | {sala['escola_id']:<12} | {escola['lat']:<12.6f} | {escola['lon']:<12.6f} | {dist:<10.3f}\n")

            f.write(separator)
            
            total_alocados = total_alunos_geral - total_nao_alocados
            media_dist = total_dist_geral / total_alocados if total_alocados > 0 else 0
            
            f.write(f"Alunos Totais (TODAS AS ETAPAS): {total_alunos_geral}\n")
            f.write(f"Alunos Não Alocados: {total_nao_alocados}\n")
            f.write(f"Distância Total Percorrida (Real): {total_dist_geral:.2f} km\n")
            f.write(f"Distância Média por Aluno (Alocados): {media_dist:.3f} km\n")

        elapsed_total = time.time() - start_time_total
        print(f"\nTempo total de execução: {elapsed_total:.2f} segundos.")
        print(f"Resultados detalhados salvos em: {output_filename}")

    except Exception as e:
        print(f"\n✗ ERRO ao salvar arquivo de resultados: {e}")