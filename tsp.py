"""Resolve o Problema do Caixeiro Viajante usando um algoritmo genetico.

O Problema do Caixeiro Viajante (TSP) procura a menor rota que passa por
todas as cidades e retorna ao ponto inicial. Neste programa, cada possivel
rota e um "individuo" e um conjunto de rotas e chamado de "populacao".

O programa tambem usa o Pygame para mostrar, em tempo real, a melhor rota
encontrada e um grafico com a evolucao da distancia.
"""

# Bibliotecas externas e modulos do projeto.
import pygame
from pygame.locals import *  # Constantes do Pygame, como QUIT e KEYDOWN.
import random  # Usado para escolher os pais de forma aleatoria.
import itertools  # Fornece um contador de geracoes que cresce continuamente.
import sys  # Usado para encerrar completamente o programa.
import numpy as np  # Facilita calculos numericos e de probabilidades.

# Funcoes que implementam as etapas do algoritmo genetico.
from genetic_algorithm import (
    mutate,
    order_crossover,
    generate_random_population,
    calculate_fitness,
    sort_population,
    default_problems,
)

# Funcoes responsaveis por desenhar o grafico, as cidades e as rotas.
from draw_functions import draw_paths, draw_plot, draw_cities

# Importa os dados do problema ATT48: coordenadas e melhor ordem conhecida.
from benchmark_att48 import *


# ---------------------------------------------------------------------------
# CONFIGURACOES DA JANELA (PYGAME)
# ---------------------------------------------------------------------------

# Tamanho inicial da janela. Mais abaixo ele sera alterado para o ATT48.
WIDTH, HEIGHT = 800, 400

# Raio, em pixels, do circulo usado para representar cada cidade.
NODE_RADIUS = 10

# Quantidade maxima de atualizacoes da tela por segundo.
FPS = 30

# Reserva a parte esquerda da janela para o grafico. As cidades comecam depois
# desta posicao horizontal.
PLOT_X_OFFSET = 450


# ---------------------------------------------------------------------------
# CONFIGURACOES DO ALGORITMO GENETICO (GA = Genetic Algorithm)
# ---------------------------------------------------------------------------

# Quantidade de cidades. Esta configuracao seria usada nos exemplos aleatorios;
# o benchmark ativo possui 48 cidades.
N_CITIES = 15

# Quantidade de rotas candidatas mantidas em cada geracao.
POPULATION_SIZE = 100

# Esta variavel nao e usada no laco atual. Como vale None, o programa continua
# criando geracoes ate o usuario fechar a janela ou pressionar Q.
N_GENERATIONS = None

# Chance de uma rota filha sofrer mutacao. 0.5 corresponde a 50%.
MUTATION_PROBABILITY = 0.5


# Cores no formato RGB: (vermelho, verde, azul). Cada valor vai de 0 a 255.
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)


# ---------------------------------------------------------------------------
# ESCOLHA E PREPARACAO DO PROBLEMA
# ---------------------------------------------------------------------------

# Alternativa 1 (desativada): criar cidades em posicoes aleatorias.
# cities_locations = [
#     (
#         random.randint(NODE_RADIUS + PLOT_X_OFFSET, WIDTH - NODE_RADIUS),
#         random.randint(NODE_RADIUS, HEIGHT - NODE_RADIUS),
#     )
#     for _ in range(N_CITIES)
# ]

# Alternativa 2 (desativada): usar um problema padrao de 10, 12 ou 15 cidades.
# WIDTH, HEIGHT = 800, 400
# cities_locations = default_problems[15]

# Alternativa 3 (ativa): usar o benchmark ATT48, com 48 cidades.
# A janela e aumentada para comportar o problema e o grafico.
WIDTH, HEIGHT = 1500, 800

# Converte as coordenadas importadas para um array numerico do NumPy.
att_cities_locations = np.array(att_48_cities_locations)

# Descobre os maiores valores dos eixos X e Y nas coordenadas originais.
max_x = max(point[0] for point in att_cities_locations)
max_y = max(point[1] for point in att_cities_locations)

# Calcula fatores de escala para fazer todas as cidades caberem na janela.
# No eixo X, desconta-se o espaco reservado para o grafico e para o raio.
scale_x = (WIDTH - PLOT_X_OFFSET - NODE_RADIUS) / max_x
scale_y = HEIGHT / max_y

# Cria uma nova lista de coordenadas ajustadas para a tela.
# int() transforma os resultados em numeros inteiros, exigidos para os pixels.
cities_locations = [
    (
        int(point[0] * scale_x + PLOT_X_OFFSET),
        int(point[1] * scale_y),
    )
    for point in att_cities_locations
]

# Monta a melhor rota conhecida do ATT48. O "- 1" e necessario porque os
# indices da lista Python comecam em 0, mas a ordem do benchmark comeca em 1.
target_solution = [cities_locations[i - 1] for i in att_48_cities_order]

# Fitness, neste projeto, representa a distancia total da rota. Portanto,
# quanto MENOR o valor, MELHOR e a solucao.
fitness_target_solution = calculate_fitness(target_solution)
print(f"Best Solution: {fitness_target_solution}")


# ---------------------------------------------------------------------------
# INICIALIZACAO DA INTERFACE GRAFICA
# ---------------------------------------------------------------------------

# Prepara os recursos internos do Pygame.
pygame.init()

# Cria a janela com o tamanho definido anteriormente.
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("TSP Solver using Pygame")

# Este relogio sera usado para limitar a velocidade do laco principal.
clock = pygame.time.Clock()

# Cria um contador infinito: cada chamada de next() retorna 1, 2, 3 etc.
generation_counter = itertools.count(start=1)


# ---------------------------------------------------------------------------
# CRIACAO DA POPULACAO INICIAL
# ---------------------------------------------------------------------------

# Gera 100 rotas aleatorias, pois POPULATION_SIZE vale 100.
# Cada rota contem todas as cidades em uma ordem diferente.
# TODO: testar heuristicas como Vizinho Mais Proximo ou Fecho Convexo para
# produzir uma populacao inicial possivelmente melhor.
population = generate_random_population(cities_locations, POPULATION_SIZE)

# Guardam o historico para desenhar o grafico e consultar solucoes anteriores.
best_fitness_values = []
best_solutions = []


# ---------------------------------------------------------------------------
# LACO PRINCIPAL: CADA REPETICAO PRODUZ UMA NOVA GERACAO
# ---------------------------------------------------------------------------

running = True
while running:
    # Le todos os eventos ocorridos desde a ultima atualizacao da tela.
    for event in pygame.event.get():
        # Encerra ao clicar no X da janela.
        if event.type == pygame.QUIT:
            running = False
        # Tambem encerra quando uma tecla e pressionada e essa tecla e Q.
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                running = False

    # Obtem o numero da geracao atual e limpa a tela com a cor branca.
    generation = next(generation_counter)
    screen.fill(WHITE)

    # Calcula a distancia total (fitness) de cada rota da populacao.
    population_fitness = [
        calculate_fitness(individual) for individual in population
    ]

    # Ordena rotas e fitness do menor para o maior. Depois disso, o item de
    # indice 0 e a melhor rota encontrada nesta geracao.
    population, population_fitness = sort_population(
        population, population_fitness
    )

    # Registra a melhor rota da geracao e sua distancia.
    best_solution = population[0]
    best_fitness = population_fitness[0]
    best_fitness_values.append(best_fitness)
    best_solutions.append(best_solution)

    # Desenha o historico da menor distancia encontrada em cada geracao.
    draw_plot(
        screen,
        list(range(len(best_fitness_values))),
        best_fitness_values,
        y_label="Fitness - Distance (pxls)",
    )

    # Desenha as cidades em vermelho, a melhor rota em azul e a segunda melhor
    # em cinza. A rota azul usa uma linha mais grossa para ganhar destaque.
    draw_cities(screen, cities_locations, RED, NODE_RADIUS)
    draw_paths(screen, best_solution, BLUE, width=3)
    draw_paths(screen, population[1], rgb_color=(128, 128, 128), width=1)

    # Exibe no terminal o progresso do algoritmo.
    print(f"Generation {generation}: Best fitness = {round(best_fitness, 2)}")

    # ELITISMO: copia a melhor rota diretamente para a proxima geracao. Assim,
    # uma boa solucao nunca e perdida por causa do cruzamento ou da mutacao.
    new_population = [population[0]]

    # Continua criando filhos ate completar novamente 100 individuos.
    while len(new_population) < POPULATION_SIZE:
        # SELECAO: como distancia menor e melhor, usamos o inverso do fitness.
        # Dessa forma, rotas curtas recebem maior peso e maior chance de serem
        # escolhidas como pais, mas as demais ainda podem ser selecionadas.
        probability = 1 / np.array(population_fitness)
        parent1, parent2 = random.choices(
            population, weights=probability, k=2
        )

        # CROSSOVER: deveria combinar partes de dois pais para gerar um filho.
        # ATENCAO: o codigo original passa parent1 duas vezes. Assim, parent2 e
        # selecionado, mas nao e utilizado. Para cruzar pais diferentes, troque
        # a linha abaixo por: child1 = order_crossover(parent1, parent2)
        child1 = order_crossover(parent1, parent1)

        # MUTACAO: pode alterar a ordem de algumas cidades no filho. Isso ajuda
        # a criar diversidade e a explorar novas rotas.
        child1 = mutate(child1, MUTATION_PROBABILITY)

        # Insere o novo filho na populacao da proxima geracao.
        new_population.append(child1)

    # Substitui a populacao atual pela populacao recem-criada.
    population = new_population

    # Mostra na janela tudo o que foi desenhado nesta repeticao.
    pygame.display.flip()

    # Limita o laco a FPS (30) repeticoes por segundo.
    clock.tick(FPS)


# TODO: futuramente, salvar em arquivo a melhor rota caso ela seja melhor que
# uma solucao salva anteriormente.

# Libera os recursos do Pygame e encerra o processo Python.
pygame.quit()
sys.exit()
