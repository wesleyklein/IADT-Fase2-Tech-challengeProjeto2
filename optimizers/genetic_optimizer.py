"""Implementação incremental do algoritmo genético."""
import random

from genetic_algorithm import calculate_fitness, generate_random_population, mutate, order_crossover, sort_population
from .base_optimizer import RouteOptimizer


class GeneticOptimizer(RouteOptimizer):
    """Avança uma geração por chamada de :meth:`step`."""
    def initialize(self, cities, config) -> None:
        self.config = config
        self.cities = list(cities)
        self.random = random.Random(config.random_seed)
        self.population = self._population()
        self.generation = 0
        self.history: list[float] = []
        self.best_route: list = []
        self.best_fitness = float("inf")

    def _population(self):
        return [self.random.sample(self.cities, len(self.cities)) for _ in range(self.config.population_size)]

    def step(self) -> None:
        if self.is_finished():
            return
        fitness = [calculate_fitness(route) for route in self.population]
        self.population, fitness = sort_population(self.population, fitness)
        if fitness[0] < self.best_fitness:
            self.best_fitness, self.best_route = fitness[0], list(self.population[0])
        self.history.append(self.best_fitness)
        elites = [list(route) for route in self.population[:self.config.elite_count]]
        weights = [1.0 / max(value, 1e-12) for value in fitness]
        new_population = elites
        # As funções legadas usam o módulo random; preservar o estado global torna
        # cada execução reproduzível sem contaminar o restante da aplicação.
        state = random.getstate()
        random.setstate(self.random.getstate())
        try:
            while len(new_population) < self.config.population_size:
                parent1, parent2 = random.choices(self.population, weights=weights, k=2)
                child = order_crossover(parent1, parent2)
                new_population.append(mutate(child, self.config.mutation_probability))
            self.random.setstate(random.getstate())
        finally:
            random.setstate(state)
        self.population = new_population
        self.generation += 1

    def is_finished(self) -> bool:
        return self.generation >= self.config.generations

    def get_best_route(self): return list(self.best_route)
    def get_best_fitness(self): return self.best_fitness
    def get_history(self): return list(self.history)
