"""Otimizadores incrementais para o cenário hospitalar."""
import random
from routing import HospitalRoutingEvaluator
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
        self.generation=0; self.history=[]; self.best_route=[]; self.best_fitness=float("inf"); self.best_solution=None
    def step(self):
        if self.is_finished(): return
        ranked=sorted(((self.evaluator.evaluate(x),x) for x in self.population),key=lambda x:x[0])
        if ranked[0][0]<self.best_fitness:
            self.best_fitness,self.best_route=ranked[0][0],list(ranked[0][1]); self.best_solution=self.evaluator.decode(self.best_route)
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

class HospitalGreedyOptimizer(RouteOptimizer):
    def initialize(self, scenario, config):
        self.scenario=scenario; self.config=config; self.finished=False; self.history=[]; self.best_route=[]; self.best_fitness=float("inf"); self.best_solution=None
    def step(self):
        if self.finished:return
        depot=self.scenario.depot
        remaining=list(self.scenario.deliveries); chromosome=[]; current=(depot.x_km,depot.y_km)
        while remaining:
            chosen=min(remaining,key=lambda d:((((d.x_km-current[0])**2+(d.y_km-current[1])**2)**.5/int(d.priority)),-int(d.priority),d.deadline_minutes,d.id))
            chromosome.append(chosen.id); remaining.remove(chosen); current=(chosen.x_km,chosen.y_km)
        self.best_route=chromosome; self.best_solution=HospitalRoutingEvaluator(self.scenario).decode(chromosome)
        self.best_fitness=self.best_solution.objective_cost; self.history=[self.best_fitness]; self.finished=True
    def is_finished(self): return self.finished
    def get_best_route(self): return list(self.best_route)
    def get_best_fitness(self): return self.best_fitness
    def get_history(self): return list(self.history)
    def get_best_solution(self): return self.best_solution
