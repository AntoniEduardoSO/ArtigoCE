import random
import math
import time
from collections import Counter, defaultdict
from deap import base, creator, tools, algorithms
import numpy as np

# --- OTIMIZAÇÕES PRINCIPAIS ---
# 1. Cache de distâncias (evita recalcular Haversine milhares de vezes)
# 2. Estruturas de dados otimizadas (defaultdict, arrays numpy)
# 3. Pré-filtro de salas válidas por etapa/horário
# 4. Algoritmo greedy melhorado com balanceamento de carga
# 5. Avaliação fitness otimizada (cálculo incremental)

# --- 1. Constantes de Penalidade e Otimização ---
PENALTY_MISMATCH = 10**10
PENALTY_UNASSIGNED_SPECIAL = 10**9
PENALTY_UNASSIGNED_NORMAL = 10**8
PENALTY_OVERCAPACITY = 10**7

DISTANCE_TARGET_KM = 1.2
PENALTY_DISTANCE_MULTIPLIER = 10000

N_CLOSEST_OPTIONS = 30  # Reduzido de 50 para 30 (mais focado)

# --- 2. Cache de Distâncias (OTIMIZAÇÃO CRÍTICA) ---
_distance_cache = {}

def haversine(lat1, lon1, lat2, lon2):
    """Calcula distância com cache para evitar recálculos."""
    key = (round(lat1, 6), round(lon1, 6), round(lat2, 6), round(lon2, 6))
    if key not in _distance_cache:
        R = 6371
        dLat = math.radians(lat2 - lat1)
        dLon = math.radians(lon2 - lon1)
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        a = math.sin(dLat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dLon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        _distance_cache[key] = R * c
    return _distance_cache[key]

# --- 3. Funções de Carregamento Otimizadas ---

def load_alunos(filepath="alunos.txt"):
    """Carrega alunos de forma otimizada."""
    alunos = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            total = int(f.readline().strip())
            for line in f:
                parts = line.split()
                if len(parts) >= 6:
                    alunos.append({
                        "id": parts[0],
                        "lat": float(parts[1]),
                        "lon": float(parts[2]),
                        "etapa": int(parts[3]),
                        "horario": int(parts[4]),
                        "special": int(parts[5])
                    })
        print(f"✓ Carregados {len(alunos)} alunos (esperado: {total})")
        return alunos
    except Exception as e:
        print(f"✗ ERRO ao carregar alunos: {e}")
        return None

def load_escolas(filepath="escolas.txt"):
    """Carrega escolas de forma otimizada."""
    escolas = {}
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            total = int(f.readline().strip())
            for line in f:
                parts = line.split()
                if len(parts) >= 3:
                    escolas[int(parts[0])] = {
                        "lat": float(parts[1]),
                        "lon": float(parts[2])
                    }
        print(f"✓ Carregadas {len(escolas)} escolas (esperado: {total})")
        return escolas
    except Exception as e:
        print(f"✗ ERRO ao carregar escolas: {e}")
        return None

def load_salas(filepath="salas.txt"):
    """Carrega salas de forma otimizada com índice por etapa/horário."""
    salas = {}
    salas_por_etapa_horario = defaultdict(list)  # NOVO: índice rápido
    total_vagas = 0

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            total = int(f.readline().strip())
            for line in f:
                parts = line.split()
                if len(parts) >= 5:
                    id_sala = int(parts[1])
                    escola_id = int(parts[0])
                    etapa = int(parts[2])
                    horario = int(parts[3])
                    vagas = int(parts[4])

                    salas[id_sala] = {
                        "escola_id": escola_id,
                        "etapa": etapa,
                        "horario": horario,
                        "vagas": vagas
                    }

                    # Índice para busca rápida
                    salas_por_etapa_horario[(etapa, horario)].append(id_sala)
                    total_vagas += vagas

        print(f"✓ Carregadas {len(salas)} salas com {total_vagas} vagas (esperado: {total})")
        return salas, salas_por_etapa_horario
    except Exception as e:
        print(f"✗ ERRO ao carregar salas: {e}")
        return None, None

def preprocess_aluno_salas_proximas(alunos, escolas, salas, salas_por_etapa_horario):
    """
    OTIMIZADO: Usa o índice de salas_por_etapa_horario para busca O(1)
    e pré-calcula todas as distâncias necessárias.
    """
    print("⏳ Pré-processando distâncias e opções de alocação...")
    start = time.time()

    aluno_sala_map = []
    alunos_sem_opcoes = 0
    unfound_combos = Counter()

    # Pré-calcula distâncias escola-sala (evita duplicatas)
    escola_coords = {id_e: (e["lat"], e["lon"]) for id_e, e in escolas.items()}

    for idx, aluno in enumerate(alunos):
        if idx % 500 == 0 and idx > 0:
            print(f"  Processados {idx}/{len(alunos)} alunos...")

        aluno_etapa = aluno["etapa"]
        aluno_horario = aluno["horario"]
        aluno_coords = (aluno["lat"], aluno["lon"])

        # Busca rápida: apenas salas com a etapa/horário corretos
        salas_validas_ids = salas_por_etapa_horario.get((aluno_etapa, aluno_horario), [])

        if not salas_validas_ids:
            alunos_sem_opcoes += 1
            unfound_combos[(aluno_etapa, aluno_horario)] += 1
            aluno_sala_map.append([])
            continue

        # Calcula distâncias apenas para salas válidas
        salas_com_dist = []
        for id_sala in salas_validas_ids:
            escola_id = salas[id_sala]["escola_id"]
            if escola_id in escola_coords:
                escola_lat, escola_lon = escola_coords[escola_id]
                dist = haversine(aluno_coords[0], aluno_coords[1], escola_lat, escola_lon)
                salas_com_dist.append((id_sala, dist))

        # Ordena por distância (crescente)
        salas_com_dist.sort(key=lambda x: x[1])
        aluno_sala_map.append([id_sala for id_sala, _ in salas_com_dist])

    elapsed = time.time() - start
    print(f"✓ Pré-processamento concluído em {elapsed:.2f}s")
    print(f"  Cache de distâncias: {len(_distance_cache)} entradas")

    if alunos_sem_opcoes > 0:
        print(f"\n⚠ {alunos_sem_opcoes} alunos SEM opções de sala:")
        for (etapa, horario), count in unfound_combos.most_common(5):
            print(f"  • Etapa {etapa}, Horário {horario}: {count} alunos")

    return aluno_sala_map

# --- 4. Configuração DEAP ---

print("\n" + "="*60)
print("SISTEMA DE ALOCAÇÃO DE ALUNOS - VERSÃO OTIMIZADA")
print("="*60 + "\n")

ALUNOS = load_alunos("Models/alunos.txt")
ESCOLAS = load_escolas("Models/escolas.txt")
SALAS, SALAS_POR_ETAPA_HORARIO = load_salas("Models/salas.txt")

if not ALUNOS or not ESCOLAS or not SALAS:
    print("\n✗ Encerrando devido a erros no carregamento.")
    exit()

ALUNO_SALA_MAP = preprocess_aluno_salas_proximas(ALUNOS, ESCOLAS, SALAS, SALAS_POR_ETAPA_HORARIO)

UNASSIGNED_ID = -1
N_ALUNOS = len(ALUNOS)

# Análise de viabilidade
total_vagas = sum(s["vagas"] for s in SALAS.values())
print(f"\n📊 Análise de Viabilidade:")
print(f"  Total de alunos: {N_ALUNOS}")
print(f"  Total de vagas: {total_vagas}")
print(f"  Taxa de ocupação: {(N_ALUNOS/total_vagas)*100:.1f}%")

creator.create("FitnessMin", base.Fitness, weights=(-1.0,))
creator.create("Individual", list, fitness=creator.FitnessMin)

toolbox = base.Toolbox()

def create_individual_balanced_greedy():
    """
    OTIMIZADO: Greedy com balanceamento de carga.
    Evita lotar uma sala quando há alternativas próximas com espaço.
    """
    individual = [UNASSIGNED_ID] * N_ALUNOS
    sala_occupation = defaultdict(int)

    # Prioriza alunos especiais
    indices_especiais = [i for i, a in enumerate(ALUNOS) if a['special'] == 1]
    indices_normais = [i for i, a in enumerate(ALUNOS) if a['special'] == 0]

    for i in indices_especiais + indices_normais:
        salas_proximas = ALUNO_SALA_MAP[i]

        if not salas_proximas:
            continue

        # Tenta as N mais próximas, escolhendo a com mais espaço
        melhor_sala = None
        melhor_score = float('inf')

        for id_sala in salas_proximas[:N_CLOSEST_OPTIONS]:
            vagas = SALAS[id_sala]["vagas"]
            ocupacao = sala_occupation[id_sala]

            if ocupacao < vagas:
                # Score = posição na lista (distância) + penalidade por ocupação
                idx_dist = salas_proximas.index(id_sala)
                score = idx_dist + (ocupacao / vagas) * 10

                if score < melhor_score:
                    melhor_score = score
                    melhor_sala = id_sala

        if melhor_sala:
            individual[i] = melhor_sala
            sala_occupation[melhor_sala] += 1
        else:
            # Se todas estão cheias, pega a mais próxima mesmo
            individual[i] = salas_proximas[0]
            sala_occupation[salas_proximas[0]] += 1

    return creator.Individual(individual)

toolbox.register("individual", create_individual_balanced_greedy)
toolbox.register("population", tools.initRepeat, list, toolbox.individual)

# Cache para fitness (evita recalcular)
_fitness_cache = {}

def evaluate(individual):
    """OTIMIZADO: Fitness com cálculo incremental e cache."""
    # Converte para tuple para usar como chave de cache
    ind_tuple = tuple(individual)
    if ind_tuple in _fitness_cache:
        return _fitness_cache[ind_tuple]

    total_distance = 0
    unassigned_special = 0
    unassigned_normal = 0
    overcapacity_penalty = 0
    mismatch_count = 0
    penalty_long_distance = 0

    # Conta ocupação (mais rápido com Counter)
    sala_counts = Counter(individual)

    # 1. Penalidade por superlotação
    for id_sala, count in sala_counts.items():
        if id_sala != UNASSIGNED_ID and id_sala in SALAS:
            vagas = SALAS[id_sala]["vagas"]
            if count > vagas:
                overcapacity_penalty += (count - vagas) * PENALTY_OVERCAPACITY

    # 2. Penalidades individuais
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

        # Validação etapa/horário
        if sala['etapa'] != aluno['etapa'] or sala['horario'] != aluno['horario']:
            mismatch_count += 1
            continue

        escola_id = sala["escola_id"]
        if escola_id not in ESCOLAS:
            mismatch_count += 1
            continue

        # Distância (usa cache do haversine)
        escola = ESCOLAS[escola_id]
        dist = haversine(aluno["lat"], aluno["lon"], escola["lat"], escola["lon"])
        total_distance += dist

        if dist > DISTANCE_TARGET_KM:
            penalty_long_distance += ((dist - DISTANCE_TARGET_KM)**2) * PENALTY_DISTANCE_MULTIPLIER

    final_score = (
        mismatch_count * PENALTY_MISMATCH +
        unassigned_special * PENALTY_UNASSIGNED_SPECIAL +
        unassigned_normal * PENALTY_UNASSIGNED_NORMAL +
        overcapacity_penalty +
        penalty_long_distance +
        total_distance
    )

    result = (final_score,)
    _fitness_cache[ind_tuple] = result
    return result

def custom_mutate(individual, indpb):
    """Mutação inteligente: favorece trocas que reduzem superlotação."""
    sala_counts = Counter(individual)

    for i in range(len(individual)):
        if random.random() < indpb:
            salas_proximas = ALUNO_SALA_MAP[i]

            if not salas_proximas or len(salas_proximas) == 1:
                continue

            sala_atual = individual[i]
            opcoes = salas_proximas[:N_CLOSEST_OPTIONS]

            # Se a sala atual está superlotada, força mudança
            if sala_atual in SALAS:
                vagas_atual = SALAS[sala_atual]["vagas"]
                if sala_counts[sala_atual] > vagas_atual:
                    # Escolhe sala com mais espaço
                    opcoes_espaco = [(s, SALAS[s]["vagas"] - sala_counts[s])
                                     for s in opcoes if s in SALAS]
                    opcoes_espaco.sort(key=lambda x: x[1], reverse=True)
                    if opcoes_espaco and opcoes_espaco[0][1] > 0:
                        individual[i] = opcoes_espaco[0][0]
                        continue

            # Mutação normal
            nova_sala = random.choice(opcoes)
            if nova_sala != sala_atual:
                individual[i] = nova_sala

    return individual,

toolbox.register("evaluate", evaluate)
toolbox.register("mate", tools.cxUniform, indpb=0.5)
toolbox.register("mutate", custom_mutate, indpb=0.03)
toolbox.register("select", tools.selTournament, tournsize=3)

# --- 5. Execução Otimizada ---

def main():
    start_time = time.time()

    # PARÂMETROS OTIMIZADOS para dataset grande
    MU = 200         # População reduzida (qualidade inicial já é boa)
    LAMBDA = 300     # Mais filhos para exploração
    NGEN = 200       # Gerações suficientes
    CXPB = 0.7       # Crossover alto
    MUTPB = 0.3      # Mutação moderada

    print(f"\n🚀 Iniciando Algoritmo Genético:")
    print(f"  População: {MU} | Filhos: {LAMBDA} | Gerações: {NGEN}")
    print(f"  Crossover: {CXPB} | Mutação: {MUTPB}\n")

    pop = toolbox.population(n=MU)
    hof = tools.HallOfFame(1)

    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", lambda x: np.mean([fit[0] for fit in x]))
    stats.register("min", lambda x: np.min([fit[0] for fit in x]))

    # Avalia população inicial
    print("Avaliando população inicial...")
    fitnesses = list(map(toolbox.evaluate, pop))
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit

    print(f"Fitness inicial: Melhor={min(fitnesses)[0]:.2f}, Média={np.mean([f[0] for f in fitnesses]):.2f}\n")

    # Evolução
    algorithms.eaMuPlusLambda(
        pop, toolbox,
        mu=MU,
        lambda_=LAMBDA,
        cxpb=CXPB,
        mutpb=MUTPB,
        ngen=NGEN,
        stats=stats,
        halloffame=hof,
        verbose=True
    )

    elapsed = time.time() - start_time
    print(f"\n✓ Evolução concluída em {elapsed:.2f}s ({elapsed/60:.1f} min)")
    print(f"  Cache de fitness: {len(_fitness_cache)} entradas")

    # --- 6. Análise e Saída ---

    if not hof:
        print("✗ ERRO: Nenhuma solução encontrada.")
        return

    best = hof[0]
    print(f"\n{'='*60}")
    print(f"MELHOR SOLUÇÃO ENCONTRADA")
    print(f"{'='*60}")
    print(f"Fitness total: {best.fitness.values[0]:.2f}\n")

    # Estatísticas detalhadas
    sala_counts = Counter(best)
    unassigned_special = sum(1 for i, a in enumerate(ALUNOS) if a['special'] == 1 and best[i] == UNASSIGNED_ID)
    unassigned_normal = sum(1 for i, a in enumerate(ALUNOS) if a['special'] == 0 and best[i] == UNASSIGNED_ID)

    overcapacity = sum(max(0, count - SALAS[id_s]["vagas"])
                       for id_s, count in sala_counts.items()
                       if id_s != UNASSIGNED_ID and id_s in SALAS)

    mismatch = sum(1 for i in range(N_ALUNOS)
                   if best[i] != UNASSIGNED_ID and best[i] in SALAS
                   and (SALAS[best[i]]['etapa'] != ALUNOS[i]['etapa'] or
                        SALAS[best[i]]['horario'] != ALUNOS[i]['horario']))

    distancias = []
    for i in range(N_ALUNOS):
        if best[i] != UNASSIGNED_ID and best[i] in SALAS:
            sala = SALAS[best[i]]
            if sala["escola_id"] in ESCOLAS:
                escola = ESCOLAS[sala["escola_id"]]
                dist = haversine(ALUNOS[i]["lat"], ALUNOS[i]["lon"],
                                escola["lat"], escola["lon"])
                distancias.append(dist)

    print(f"📋 Restrições Hard:")
    print(f"  ❌ Etapa/Horário incorretos: {mismatch}")
    print(f"  🔴 Alunos especiais não alocados: {unassigned_special}")
    print(f"  🟡 Alunos normais não alocados: {unassigned_normal}")
    print(f"  📦 Vagas excedidas: {overcapacity}")

    if distancias:
        print(f"\n📏 Distâncias:")
        print(f"  Total: {sum(distancias):.2f} km")
        print(f"  Média: {np.mean(distancias):.3f} km")
        print(f"  Mediana: {np.median(distancias):.3f} km")
        print(f"  Máxima: {max(distancias):.3f} km")
        print(f"  Acima de {DISTANCE_TARGET_KM}km: {sum(1 for d in distancias if d > DISTANCE_TARGET_KM)} alunos")

    # Gera arquivo de saída
    output_file = "alocacao_final.txt"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("id_aluno;necessidade_especial;id_escola;id_sala;etapa_desejada;etapa_sala;horario_desejado;horario_sala;distancia_km\n")
        for i in range(N_ALUNOS):
            aluno = ALUNOS[i]
            id_sala = best[i]

            if id_sala == UNASSIGNED_ID or id_sala not in SALAS:
                f.write(f"{aluno['id']};{aluno['special']};NAO_ALOCADO;NAO_ALOCADO;{aluno['etapa']};N/A;{aluno['horario']};N/A;N/A\n")
            else:
                sala = SALAS[id_sala]
                id_escola = sala["escola_id"]

                if id_escola in ESCOLAS:
                    dist = haversine(aluno["lat"], aluno["lon"],
                                    ESCOLAS[id_escola]["lat"], ESCOLAS[id_escola]["lon"])
                else:
                    dist = -1

                etapa_str = f"ERRO:{sala['etapa']}" if sala['etapa'] != aluno['etapa'] else sala['etapa']
                horario_str = f"ERRO:{sala['horario']}" if sala['horario'] != aluno['horario'] else sala['horario']

                f.write(f"{aluno['id']};{aluno['special']};{id_escola};{id_sala};{aluno['etapa']};{etapa_str};{aluno['horario']};{horario_str};{dist:.3f}\n")

    print(f"\n✓ Arquivo salvo: {output_file}")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
