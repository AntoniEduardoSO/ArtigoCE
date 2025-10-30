#include <stdio.h>
#include <stdlib.h>
#include <string.h> // Necessário para memset e memcpy
#include <math.h>
#include <time.h>

// --- PARÂMETROS DO ALGORITMO GENÉTICO ---
#define TAM_POPULACAO 100        // Quantos indivíduos por geração
#define N_GERACOES 200           // Quantas gerações executar
#define TAXA_MUTACAO 0.05        // 5% de chance de mutar um gene
#define TAM_TORNEIO 3            // Tamanho do torneio para seleção
#define ELITISMO 1               // 1 = Manter o melhor indivíduo; 0 = Não

// --- PENALIDADES DA FUNÇÃO DE FITNESS (MINIMIZAÇÃO) ---
#define PENALIDADE_ESTOURO_VAGA 5000.0 // Gravíssimo
#define PENALIDADE_ETAPA_ERRADA 2000.0 // Gravíssimo
#define PENALIDADE_NAO_ALOCADO 100.0   // Ruim, mas melhor que violar restrições

// --- ESTRUTURAS DE DADOS ---
typedef struct {
    int id_aluno;
    double lat;
    double lon;
    int id_etapa_desejada;
} Aluno;

typedef struct {
    int id_escola;
    double lat;
    double lon;
} Escola;

typedef struct {
    int id_sala;
    int id_escola; // Índice da escola no array 'escolas'
    int id_etapa;
    int capacidade;
} Sala;

// O CROMOSSOMO / INDIVÍDUO
typedef struct {
    int* genes;     // Array de N_ALUNOS
    double fitness; // Custo (quanto menor, melhor)
} Individuo;

// --- VARIÁVEIS GLOBAIS DE DADOS ---
int N_ALUNOS = 0;
int N_ESCOLAS = 0;
int N_SALAS = 0;

Aluno* alunos = NULL;
Escola* escolas = NULL;
Sala* salas = NULL;

// --- OTIMIZAÇÃO: BUFFER GLOBAL DE AVALIAÇÃO ---
int* buffer_uso_sala = NULL;

int encontrarSalaValidaAleatoria(int id_etapa_desejada) {
    // 1. Encontrar todas as salas válidas para esta etapa
    int salas_validas_indices[N_SALAS];
    int count = 0;

    for (int j = 0; j < N_SALAS; j++) {
        if (salas[j].id_etapa == id_etapa_desejada) {
            salas_validas_indices[count] = j; // Armazena o índice da sala
            count++;
        }
    }

    // 2. Selecionar uma aleatoriamente
    if (count > 0) {
        int idx_aleatorio = rand() % count;
        return salas_validas_indices[idx_aleatorio];
    } else {
        // Se não houver salas para a etapa, o aluno deve ser não-alocado (-1)
        return -1;
    }
}

// --- FUNÇÕES AUXILIARES (DISTÂNCIA) ---
double paraRadianos(double graus) {
    return graus * M_PI / 180.0;
}

double calcularDistancia(double lat1, double lon1, double lat2, double lon2) {
    double R = 6371.0; // Raio da Terra em km
    double dLat = paraRadianos(lat2 - lat1);
    double dLon = paraRadianos(lon2 - lon1);
    lat1 = paraRadianos(lat1);
    lat2 = paraRadianos(lat2);
    double a = sin(dLat / 2) * sin(dLat / 2) +
               cos(lat1) * cos(lat2) * sin(dLon / 2) * sin(dLon / 2);
    double c = 2 * atan2(sqrt(a), sqrt(1 - a));
    return R * c;
}

// --- FUNÇÕES DE CARREGAMENTO E LIMPEZA ---
void carregarDados() {
    FILE *f_alunos, *f_escolas, *f_salas;

    // Carregar Alunos
    f_alunos = fopen("alunos.txt", "r");
    if (f_alunos == NULL) { perror("Erro ao abrir alunos.txt"); exit(1); }
    fscanf(f_alunos, "%d", &N_ALUNOS);
    alunos = (Aluno*)malloc(N_ALUNOS * sizeof(Aluno));
    if (alunos == NULL) { perror("Falha ao alocar memoria para alunos"); exit(1); }
    for (int i = 0; i < N_ALUNOS; i++) {
        fscanf(f_alunos, "%d %lf %lf %d", &alunos[i].id_aluno, &alunos[i].lat, &alunos[i].lon, &alunos[i].id_etapa_desejada);
    }
    fclose(f_alunos);
    printf("Carregados %d alunos.\n", N_ALUNOS);

    // Carregar Escolas
    f_escolas = fopen("escolas.txt", "r");
    if (f_escolas == NULL) { perror("Erro ao abrir escolas.txt"); exit(1); }
    fscanf(f_escolas, "%d", &N_ESCOLAS);
    escolas = (Escola*)malloc(N_ESCOLAS * sizeof(Escola));
    if (escolas == NULL) { perror("Falha ao alocar memoria para escolas"); exit(1); }
    for (int i = 0; i < N_ESCOLAS; i++) {
        fscanf(f_escolas, "%d %lf %lf", &escolas[i].id_escola, &escolas[i].lat, &escolas[i].lon);
    }
    fclose(f_escolas);
    printf("Carregadas %d escolas.\n", N_ESCOLAS);

    // Carregar Salas
    f_salas = fopen("salas.txt", "r");
    if (f_salas == NULL) { perror("Erro ao abrir salas.txt"); exit(1); }
    fscanf(f_salas, "%d", &N_SALAS);
    salas = (Sala*)malloc(N_SALAS * sizeof(Sala));
    if (salas == NULL) { perror("Falha ao alocar memoria para salas"); exit(1); }
    for (int i = 0; i < N_SALAS; i++) {
        fscanf(f_salas, "%d %d %d %d", &salas[i].id_sala, &salas[i].id_escola, &salas[i].id_etapa, &salas[i].capacidade);
    }
    fclose(f_salas);
    printf("Carregadas %d salas (vagas).\n", N_SALAS);
    
    // VERIFICAÇÃO DE SEGURANÇA (IDs de escola nas salas)
    for(int i=0; i < N_SALAS; i++) {
        if (salas[i].id_escola < 0 || salas[i].id_escola >= N_ESCOLAS) {
            printf("Erro fatal: sala %d refere-se a escola %d, que e invalida (Max: %d).\n", 
                salas[i].id_sala, salas[i].id_escola, N_ESCOLAS - 1);
            exit(1);
        }
    }
    
    // Aloca o buffer de avaliação UMA VEZ
    buffer_uso_sala = (int*)malloc(N_SALAS * sizeof(int));
    if (buffer_uso_sala == NULL) {
        perror("Erro ao alocar buffer_uso_sala global");
        exit(1);
    }
}

void liberarDados() {
    if (alunos != NULL) free(alunos);
    if (escolas != NULL) free(escolas);
    if (salas != NULL) free(salas);
    if (buffer_uso_sala != NULL) free(buffer_uso_sala);
}

// --- FUNÇÕES DO ALGORITMO GENÉTICO ---

/**
 * Cria um indivíduo com genes aleatórios.
 */
void criarIndividuo(Individuo* ind) {
    ind->genes = (int*)malloc(N_ALUNOS * sizeof(int));
    
    if (ind->genes == NULL) {
        perror("Falha ao alocar 'genes' para individuo");
        fprintf(stderr, "N_ALUNOS = %d. Memoria insuficiente.\n", N_ALUNOS);
        exit(1); 
    }
    
    ind->fitness = 999999.0;
    for (int i = 0; i < N_ALUNOS; i++) {
        // Aluno não alocado: -1
        if (rand() % 100 < 5) { // 5% de chance de não alocar
            ind->genes[i] = -1; 
        } else {
            // Busca uma sala que ofereça a etapa desejada pelo aluno 'i'
            ind->genes[i] = encontrarSalaValidaAleatoria(alunos[i].id_etapa_desejada);
        }
    }
}

/**
 * Libera a memória de um indivíduo.
 */
void liberarIndividuo(Individuo* ind) {
    if (ind->genes != NULL) {
        free(ind->genes);
        ind->genes = NULL;
    }
}

/**
 * Copia os genes e fitness de 'origem' para 'destino'.
 */
void copiarIndividuo(Individuo* origem, Individuo* destino) {
    if (origem == NULL || destino == NULL) {
        printf("!!! ERRO FATAL: copiarIndividuo recebeu ponteiro NULL.\n"); fflush(stdout); exit(1);
    }
    if (origem->genes == NULL || destino->genes == NULL) {
        printf("!!! ERRO FATAL: copiarIndividuo recebeu genes NULL.\n"); fflush(stdout); exit(1);
    }

    memcpy(destino->genes, origem->genes, N_ALUNOS * sizeof(int));
    destino->fitness = origem->fitness;
}

/**
 * AVALIAÇÃO (FITNESS) - OTIMIZADO
 */
void avaliarIndividuo(Individuo* ind) {
    double custo_total = 0.0;
    
    // Verificações de segurança
    if (ind == NULL) {
        printf("!!! ERRO FATAL: avaliarIndividuo recebeu ind NULL.\n"); fflush(stdout); exit(1);
    }
    if (ind->genes == NULL) {
        printf("!!! ERRO FATAL: avaliarIndividuo recebeu ind->genes NULL.\n"); fflush(stdout); exit(1);
    }
    if (buffer_uso_sala == NULL) {
        printf("!!! ERRO FATAL: buffer_uso_sala e NULL.\n"); fflush(stdout); exit(1);
    }
    
    memset(buffer_uso_sala, 0, N_SALAS * sizeof(int));

    // 2. Iterar por cada gene (aluno)
    for (int i = 0; i < N_ALUNOS; i++) {
        int id_sala_alocada = ind->genes[i]; 

        // CASO 1: Aluno não alocado
        if (id_sala_alocada == -1) {
            custo_total += PENALIDADE_NAO_ALOCADO;
            continue;
        }

        // --- Verificação de segurança (gene inválido) ---
        if (id_sala_alocada < 0 || id_sala_alocada >= N_SALAS) {
             custo_total += 999999; 
             continue;
        }

        // CASO 2: Aluno alocado
        Aluno* aluno = &alunos[i]; 
        Sala* sala = &salas[id_sala_alocada]; 
        
        if (sala->id_escola < 0 || sala->id_escola >= N_ESCOLAS) {
             printf("!!! ERRO FATAL: id_escola invalido (%d) na sala %d!\n", sala->id_escola, id_sala_alocada);
             fflush(stdout);
             exit(1);
        }
        
        Escola* escola = &escolas[sala->id_escola]; 

        // Penalidade A: Etapa errada?
        if (aluno->id_etapa_desejada != sala->id_etapa) {
            custo_total += PENALIDADE_ETAPA_ERRADA;
        }

        // Custo: Distância
        custo_total += calcularDistancia(aluno->lat, aluno->lon, escola->lat, escola->lon);

        // Contagem de vagas (usando o buffer global)
        buffer_uso_sala[id_sala_alocada]++;
    }

    // 3. Penalidade B: Excesso de capacidade
    for (int j = 0; j < N_SALAS; j++) {
        if (buffer_uso_sala[j] > salas[j].capacidade) {
            int excesso = buffer_uso_sala[j] - salas[j].capacidade;
            custo_total += (excesso * PENALIDADE_ESTOURO_VAGA);
        }
    }

    ind->fitness = custo_total;
}

/**
 * SELEÇÃO: Torneio
 */
Individuo* selecaoTorneio(Individuo* populacao) {
    int melhor_idx = rand() % TAM_POPULACAO; 
    double melhor_fitness = populacao[melhor_idx].fitness; 

    for (int i = 1; i < TAM_TORNEIO; i++) {
        int idx = rand() % TAM_POPULACAO;
        if (populacao[idx].fitness < melhor_fitness) {
            melhor_fitness = populacao[idx].fitness;
            melhor_idx = idx;
        }
    }
    // O melhor_idx nunca será -1
    return &populacao[melhor_idx];
}

/**
 * CROSSOVER: Um Ponto
 */
void crossoverUmPonto(Individuo* pai1, Individuo* pai2, Individuo* filho1, Individuo* filho2) {
    if (pai1->genes == NULL || pai2->genes == NULL || filho1->genes == NULL || filho2->genes == NULL) {
        // *** ADICIONE ESTE LOG PARA AJUDAR A ENCONTRAR QUAL DELES ESTÁ NULL ***
        fprintf(stderr, "!!! ERRO FATAL INTERNO: Crossover recebeu genes NULL. Pai1: %p, Pai2: %p, Filho1: %p, Filho2: %p\n",
                (void*)pai1->genes, (void*)pai2->genes, (void*)filho1->genes, (void*)filho2->genes);
        fflush(stdout);
        exit(1);
    }
    
    int pontoCorte = (rand() % (N_ALUNOS - 1)) + 1; // Ponto de 1 a N_ALUNOS-1

    for (int i = 0; i < N_ALUNOS; i++) {
        if (i < pontoCorte) {
            filho1->genes[i] = pai1->genes[i];
            filho2->genes[i] = pai2->genes[i];
        } else {
            filho1->genes[i] = pai2->genes[i];
            filho2->genes[i] = pai1->genes[i];
        }
    }
}

/**
 * MUTAÇÃO
 */
void mutacao(Individuo* ind) {
    if (ind->genes == NULL) { // Verificação de segurança
        printf("!!! ERRO FATAL: Mutacao recebeu genes NULL.\n"); fflush(stdout); exit(1);
    }
    for (int i = 0; i < N_ALUNOS; i++) {
        if (((double)rand() / RAND_MAX) < TAXA_MUTACAO) {
            // Se mutar, o novo gene deve ser uma sala válida para a etapa do aluno
            if (rand() % 100 < 5) {
                 ind->genes[i] = -1; // Muta para não alocado
            } else {
                 ind->genes[i] = encontrarSalaValidaAleatoria(alunos[i].id_etapa_desejada);
            }
        }
    }
}

/**
 * Salva os genes do melhor indivíduo em um arquivo.
 */
void salvarSolucao(Individuo* ind, const char* filename) {
    FILE* f = fopen(filename, "w");
    if (f == NULL) {
        perror("Erro ao salvar solucao.txt");
        return; 
    }
    
    for (int i = 0; i < N_ALUNOS; i++) {
        fprintf(f, "%d\n", ind->genes[i]);
    }
    
    fclose(f);
    printf("Melhor solucao salva em '%s'\n", filename);
}

void gerarRelatorioDetalhado(Individuo* ind, const char* filename) {
    FILE* f = fopen(filename, "w");
    if (f == NULL) {
        perror("Erro ao salvar relatorio detalhado");
        return; 
    }
    
    // Cabeçalho do arquivo
    fprintf(f, "ID_ALUNO;ID_SALA_ALOCADA;ID_ESCOLA;ETAPA_DESEJADA;ETAPA_OFERECIDA;DISTANCIA_KM;CUSTO_TOTAL\n");
    
    double custo_total_recalculado = 0.0;
    
    // Usar o buffer de uso de sala para verificar a capacidade (se quiser incluir isso no relatorio)
    memset(buffer_uso_sala, 0, N_SALAS * sizeof(int));

    for (int i = 0; i < N_ALUNOS; i++) {
        int id_sala_alocada = ind->genes[i];
        Aluno* aluno = &alunos[i];
        
        // 1. Caso NÃO ALOCADO
        if (id_sala_alocada == -1) {
            double custo = PENALIDADE_NAO_ALOCADO;
            custo_total_recalculado += custo;
            
            fprintf(f, "%d;%d;NA;%d;NA;0.00;%.2f\n", 
                    aluno->id_aluno, 
                    id_sala_alocada, 
                    aluno->id_etapa_desejada, 
                    custo);
            continue;
        }

        // 2. Caso ALOCADO
        // Verificações de segurança desnecessárias aqui, pois o AG já rodou.
        Sala* sala = &salas[id_sala_alocada]; 
        Escola* escola = &escolas[sala->id_escola]; 
        
        // Custo: Distância (em km)
        double distancia_km = calcularDistancia(aluno->lat, aluno->lon, escola->lat, escola->lon);
        double custo = distancia_km;

        // Penalidade A: Etapa errada?
        if (aluno->id_etapa_desejada != sala->id_etapa) {
            custo += PENALIDADE_ETAPA_ERRADA;
        }

        // Contagem de vagas (para a penalidade de estouro, calculada depois)
        buffer_uso_sala[id_sala_alocada]++;

        // Acumula o custo (Distância + Penalidade Etapa)
        custo_total_recalculado += custo;

        // Imprime o registro detalhado
        fprintf(f, "%d;%d;%d;%d;%d;%.2f;%.2f\n", 
                aluno->id_aluno, 
                id_sala_alocada, 
                escola->id_escola,
                aluno->id_etapa_desejada, 
                sala->id_etapa, 
                distancia_km * 1000.0, // Convertendo para METROS (conforme solicitado)
                custo);
    }
    
    // 3. Penalidade B: Excesso de capacidade (Adicionada ao custo total)
    for (int j = 0; j < N_SALAS; j++) {
        if (buffer_uso_sala[j] > salas[j].capacidade) {
            int excesso = buffer_uso_sala[j] - salas[j].capacidade;
            custo_total_recalculado += (excesso * PENALIDADE_ESTOURO_VAGA);
        }
    }
    
    // Opcional: Adicionar o custo total ao final do arquivo ou em um log separado
    printf("\nCusto Total Recalculado (incluindo penalidades de capacidade): %.2f\n", custo_total_recalculado);

    fclose(f);
    printf("Relatorio detalhado salvo em '%s'\n", filename);
}

// --- FUNÇÃO PRINCIPAL (OTIMIZADA) ---
int main() {
    srand(time(NULL));

    printf("Iniciando AG de Alocacao de Alunos...\n");
    printf("Carregando dados...\n");
    carregarDados();
    printf("Dados carregados com sucesso.\n\n");

    // 1. Alocar memória para a população
    Individuo* populacao = (Individuo*)malloc(TAM_POPULACAO * sizeof(Individuo));
    Individuo* nova_populacao = (Individuo*)malloc(TAM_POPULACAO * sizeof(Individuo));
    Individuo melhor_global;
    Individuo melhor_da_geracao; 
    
    if (populacao == NULL || nova_populacao == NULL) {
        perror("Falha ao alocar arrays da populacao");
        exit(1);
    }

    // 2. Inicializar População (e alocar genes)
    printf("Alocando memoria para populacao...\n");
    for (int i = 0; i < TAM_POPULACAO; i++) {
        criarIndividuo(&populacao[i]);
        criarIndividuo(&nova_populacao[i]);
    }
    criarIndividuo(&melhor_global);
    criarIndividuo(&melhor_da_geracao); 
    
    melhor_global.fitness = 9999999.0;
    printf("Memoria da populacao alocada com sucesso.\n"); 

    printf("Iniciando loop evolucionario (%d geracoes)...\n", N_GERACOES);
    
    // 3. Loop Evolucionário Principal
    for (int ger = 0; ger < N_GERACOES; ger++) {
        
        melhor_da_geracao.fitness = 9999999.0;

        // a. Avaliação
        for (int i = 0; i < TAM_POPULACAO; i++) {
            avaliarIndividuo(&populacao[i]);

            if (populacao[i].fitness < melhor_da_geracao.fitness) {
                copiarIndividuo(&populacao[i], &melhor_da_geracao);
            }
        }

        // b. Atualizar Melhor Global
        if (melhor_da_geracao.fitness < melhor_global.fitness) {
            copiarIndividuo(&melhor_da_geracao, &melhor_global);
        }
        
        // c. Geração (Seleção, Crossover, Mutação)
        int idx_nova_pop = 0;
        
        // Elitismo
        if (ELITISMO) {
            copiarIndividuo(&melhor_global, &nova_populacao[idx_nova_pop]);
            idx_nova_pop++;
        }
        
        // --- INÍCIO DA LÓGICA DE GERAÇÃO CORRIGIDA ---
        while (idx_nova_pop < TAM_POPULACAO) {
            Individuo* pai1 = selecaoTorneio(populacao);
            Individuo* pai2 = selecaoTorneio(populacao);
            
            // Pega o primeiro filho
            Individuo* filho1 = &nova_populacao[idx_nova_pop];
            if (filho1->genes == NULL) {
                printf("!!! ERRO FATAL: filho1 (nova_populacao[%d]) tem genes NULL.\n", idx_nova_pop);
                fflush(stdout);
                exit(1);
            }

            // Verifica se ainda há espaço para o segundo filho
            if (idx_nova_pop + 1 < TAM_POPULACAO) {
                // Há espaço para 2 filhos
                Individuo* filho2 = &nova_populacao[idx_nova_pop + 1];
                if (filho2->genes == NULL) {
                    printf("!!! ERRO FATAL: filho2 (nova_populacao[%d]) tem genes NULL.\n", idx_nova_pop + 1);
                    fflush(stdout);
                    exit(1);
                }
                
                crossoverUmPonto(pai1, pai2, filho1, filho2); 
                mutacao(filho1);
                mutacao(filho2);
                
                idx_nova_pop += 2; // Avança 2 posições
            } else {
                // Só há espaço para 1 filho
                crossoverUmPonto(pai1, pai2, filho1, filho1); // Usa filho1 como placeholder
                mutacao(filho1);
                
                idx_nova_pop += 1; // Avança 1 posição (e sai do loop)
            }
        }
        // --- FIM DA LÓGICA DE GERAÇÃO CORRIGIDA ---

        
        // d. Substituição: A nova população vira a população atual
        Individuo* temp_ptr = populacao;
        populacao = nova_populacao;
        nova_populacao = temp_ptr;
        
        // Log
        if (ger % 10 == 0 || ger == N_GERACOES - 1) { 
            printf("Geracao [%d/%d] - Melhor Custo (Fitness): %.2f\n", 
                   ger, N_GERACOES, melhor_global.fitness);
        }
    }

    // 4. Exibir Resultado Final
    printf("\n--- AG CONCLUIDO ---\n");
    printf("Melhor Fitness (Custo) encontrado: %.2f\n", melhor_global.fitness);
    
    // Salvar a solução para o verificador
    salvarSolucao(&melhor_global, "solucao.txt");
    gerarRelatorioDetalhado(&melhor_global, "solucao_completa.txt");

    printf("Melhor Alocacao:\n");
    int alocados = 0;
    int nao_alocados = 0;
    memset(buffer_uso_sala, 0, N_SALAS * sizeof(int));
    for (int i = 0; i < N_ALUNOS; i++) {
        int id_sala = melhor_global.genes[i];
        if (id_sala == -1) {
            nao_alocados++;
        } else {
             // Verificação de segurança final
            if (id_sala >= 0 && id_sala < N_SALAS) {
                buffer_uso_sala[id_sala]++;
            }
            alocados++;
        }
        if (i < 10) { 
             printf("  Aluno %d -> Sala %d\n", alunos[i].id_aluno, id_sala);
        }
    }
    printf("  ... (e mais %d alocacoes)\n", N_ALUNOS - 10);
    
    printf("\nResumo da Alocacao:\n");
    int violacoes_finais = 0;
    for(int i=0; i < N_SALAS; i++) {
        if (buffer_uso_sala[i] > salas[i].capacidade) {
            printf("  *** VIOLACAO: Sala %d (Cap: %d): Usadas %d vagas ***\n", 
                   salas[i].id_sala, salas[i].capacidade, buffer_uso_sala[i]);
            violacoes_finais++;
        }
    }
    if (violacoes_finais == 0) {
        printf("  Nenhuma violacao de capacidade encontrada na solucao final.\n");
    }
    printf("Total Alocados: %d | Total Nao Alocados: %d\n", alocados, nao_alocados);


    // 5. Liberar toda a memória
    printf("\nLimpando memoria...\n");
    for (int i = 0; i < TAM_POPULACAO; i++) {
        liberarIndividuo(&populacao[i]);
        liberarIndividuo(&nova_populacao[i]);
    }
    liberarIndividuo(&melhor_global);
    liberarIndividuo(&melhor_da_geracao); 
    free(populacao);
    free(nova_populacao);
    liberarDados(); 

    printf("Concluido.\n");
    return 0;
}