import random
from genetic_algorithm import calculate_fitness, generate_random_population, mutate, order_crossover

CITIES=[(0,0),(2,0),(2,2),(0,2),(1,3)]

def test_fitness_includes_return_to_start(): assert calculate_fitness([(0,0),(3,0),(3,4)]) == 12
def test_population_size_and_permutations():
    population=generate_random_population(CITIES,7)
    assert len(population)==7 and all(set(route)==set(CITIES) for route in population)
def test_crossover_is_valid_and_does_not_change_parents():
    first=list(CITIES); second=list(reversed(CITIES)); copies=(list(first),list(second))
    random.seed(2); child=order_crossover(first,second)
    assert len(child)==len(first) and set(child)==set(first) and len(set(child))==len(child)
    assert (first,second)==copies
def test_mutation_preserves_permutation_and_parent():
    original=list(CITIES); child=mutate(original,1)
    assert set(child)==set(original) and original==CITIES
