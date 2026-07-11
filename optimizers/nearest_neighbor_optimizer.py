"""Heurística determinística do vizinho mais próximo."""
from genetic_algorithm import calculate_distance, calculate_fitness
from .base_optimizer import RouteOptimizer


def _route_from(cities, start):
    remaining = list(enumerate(cities))
    start_pair = remaining.pop(start)
    route = [start_pair[1]]
    current = start_pair[1]
    while remaining:
        position = min(range(len(remaining)), key=lambda i: (calculate_distance(current, remaining[i][1]), remaining[i][0]))
        _, current = remaining.pop(position)
        route.append(current)
    return route


def nearest_neighbor_route(cities) -> list:
    """Testa todas as cidades iniciais e devolve a melhor rota sem alterar a entrada."""
    source = list(cities)
    if len(source) <= 1:
        return source
    routes = (_route_from(source, start) for start in range(len(source)))
    return min(routes, key=lambda route: (calculate_fitness(route), source.index(route[0])))


class NearestNeighborOptimizer(RouteOptimizer):
    def initialize(self, cities, config) -> None:
        self.cities, self.finished = list(cities), False
        self.route, self.fitness, self.history = [], float("inf"), []

    def step(self) -> None:
        if not self.finished:
            self.route = nearest_neighbor_route(self.cities)
            self.fitness = calculate_fitness(self.route)
            self.history = [self.fitness]
            self.finished = True

    def is_finished(self): return self.finished
    def get_best_route(self): return list(self.route)
    def get_best_fitness(self): return self.fitness
    def get_history(self): return list(self.history)
