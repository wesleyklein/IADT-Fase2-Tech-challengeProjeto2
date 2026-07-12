"""Otimizadores incrementais para o cenário hospitalar."""
import random
from routing import HospitalRoutingEvaluator
from routing import euclidean_distance_km, travel_time_minutes
from .base_optimizer import RouteOptimizer

def _ox1(a,b,rng):
    if len(a)<2: return list(a)
    start,end=sorted(rng.sample(range(len(a)+1),2)); child=[None]*len(a); child[start:end]=a[start:end]
    remaining=[x for x in b if x not in child]; positions=[i for i,x in enumerate(child) if x is None]
    for i,x in zip(positions,remaining): child[i]=x
    return child

class HospitalGeneticOptimizer(RouteOptimizer):
    def initialize(self, scenario, config):
        self.scenario=scenario; self.config=config; self.evaluator=HospitalRoutingEvaluator(scenario); self.random=random.Random(config.random_seed)
        genes=[d.id for d in scenario.deliveries]; self.population=[self.random.sample(genes,len(genes)) for _ in range(config.population_size)]
        self.generation=0; self.history=[]; self.metrics_history=[]; self.best_route=[]; self.best_fitness=float("inf"); self.best_solution=None
    def step(self):
        if self.is_finished(): return
        ranked=sorted(((self.evaluator.evaluate(x),x) for x in self.population),key=lambda x:x[0])
        generation_solution=self.evaluator.decode(ranked[0][1])
        if ranked[0][0]<self.best_fitness:
            self.best_fitness,self.best_route=ranked[0][0],list(ranked[0][1]); self.best_solution=generation_solution
        from execution.models import HospitalGenerationMetric
        self.metrics_history.append(HospitalGenerationMetric(self.generation+1,generation_solution.objective_cost,generation_solution.total_distance_km,generation_solution.total_delay_minutes,len(generation_solution.unassigned_deliveries),sum(bool(route.stops) for route in generation_solution.routes)))
        self.history.append(self.best_fitness); elites=[list(x) for _,x in ranked[:self.config.elite_count]]
        weights=[1/max(f,1e-12) for f,_ in ranked]; population=[x for _,x in ranked]; new=elites
        while len(new)<self.config.population_size:
            a,b=self.random.choices(population,weights=weights,k=2); child=_ox1(a,b,self.random)
            if len(child)>1 and self.random.random()<self.config.mutation_probability:
                i,j=self.random.sample(range(len(child)),2); child[i],child[j]=child[j],child[i]
            new.append(child)
        self.population=new; self.generation+=1
    def is_finished(self): return self.generation>=self.config.generations
    def get_best_route(self): return list(self.best_route)
    def get_best_fitness(self): return self.best_fitness
    def get_history(self): return list(self.history)
    def get_best_solution(self): return self.best_solution
    def get_metrics_history(self): return list(self.metrics_history)

class HospitalGreedyOptimizer(RouteOptimizer):
    def initialize(self, scenario, config):
        self.scenario=scenario; self.config=config; self.finished=False; self.history=[]; self.metrics_history=[]; self.best_route=[]; self.best_fitness=float("inf"); self.best_solution=None
    def step(self):
        if self.finished:return
        depot=self.scenario.depot
        remaining=list(self.scenario.deliveries); chromosome=[]
        weights=self.scenario.fitness_weights
        for vehicle in self.scenario.vehicles:
            current=(depot.x_km,depot.y_km); load=distance=elapsed=0.0
            while remaining:
                feasible=[]
                for delivery in remaining:
                    leg=euclidean_distance_km(*current,delivery.x_km,delivery.y_km)
                    back=euclidean_distance_km(delivery.x_km,delivery.y_km,depot.x_km,depot.y_km)
                    if load+delivery.weight_kg>vehicle.capacity_kg or distance+leg+back>vehicle.autonomy_km:continue
                    arrival=elapsed+travel_time_minutes(leg,vehicle.average_speed_kmh)
                    delay=max(0.0,arrival-delivery.deadline_minutes)
                    multiplier={1:weights.regular_delay_multiplier,3:weights.high_delay_multiplier,5:weights.critical_delay_multiplier}[int(delivery.priority)]
                    score=leg/int(delivery.priority)+delay*weights.delay_weight*multiplier
                    feasible.append((score,-int(delivery.priority),delivery.deadline_minutes,leg,delivery.id,delivery))
                if not feasible:break
                chosen=min(feasible)[-1]; leg=euclidean_distance_km(*current,chosen.x_km,chosen.y_km)
                chromosome.append(chosen.id);remaining.remove(chosen);load+=chosen.weight_kg;distance+=leg
                elapsed+=travel_time_minutes(leg,vehicle.average_speed_kmh)+chosen.service_time_minutes;current=(chosen.x_km,chosen.y_km)
        chromosome.extend(delivery.id for delivery in remaining)
        self.best_route=chromosome; self.best_solution=HospitalRoutingEvaluator(self.scenario).decode(chromosome)
        self.best_fitness=self.best_solution.objective_cost; self.history=[self.best_fitness]; self.finished=True
    def is_finished(self): return self.finished
    def get_best_route(self): return list(self.best_route)
    def get_best_fitness(self): return self.best_fitness
    def get_history(self): return list(self.history)
    def get_best_solution(self): return self.best_solution
    def get_metrics_history(self): return list(self.metrics_history)
