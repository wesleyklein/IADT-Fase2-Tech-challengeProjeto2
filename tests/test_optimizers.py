from execution.models import ExecutionConfig
from genetic_algorithm import calculate_fitness
from optimizers import GeneticOptimizer, nearest_neighbor_route

CITIES=[(0,0),(1,0),(5,0),(5,1),(0,1)]

def config(**changes):
    values=dict(population_size=8,generations=4,executions=1,mutation_probability=.2,elite_count=2,random_seed=10)
    values.update(changes); return ExecutionConfig(**values)

def test_nearest_neighbor_edge_cases_and_input_preserved():
    assert nearest_neighbor_route([])==[] and nearest_neighbor_route([(1,2)])==[(1,2)]
    source=list(CITIES); route=nearest_neighbor_route(source)
    assert source==CITIES and len(route)==len(source) and set(route)==set(source)

def test_nearest_neighbor_selects_best_start():
    route=nearest_neighbor_route(CITIES)
    from optimizers.nearest_neighbor_optimizer import _route_from
    assert calculate_fitness(route)<=calculate_fitness(_route_from(CITIES,0))

def test_genetic_finishes_exactly_and_keeps_global_best():
    optimizer=GeneticOptimizer(); optimizer.initialize(CITIES,config())
    seen=[]
    while not optimizer.is_finished(): optimizer.step(); seen.append(optimizer.get_best_fitness())
    assert optimizer.generation==4 and len(optimizer.get_history())==4
    assert optimizer.get_best_fitness()==min(seen)

def test_elites_are_copied_into_next_population():
    optimizer=GeneticOptimizer(); optimizer.initialize(CITIES,config(generations=1))
    optimizer.step()
    assert optimizer.get_best_route() in optimizer.population[:2]
