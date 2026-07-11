"""Orquestrador incremental, sem dependência do Pygame."""
import secrets
import time
from dataclasses import replace

from optimizers import GeneticOptimizer, NearestNeighborOptimizer
from .models import ComparisonResult, ProcessingState, RunResult
from .statistics import consolidate, improvement_percentage


class ExperimentRunner:
    def __init__(self, cities):
        self.cities = list(cities)
        self.clear()

    def clear(self):
        self.state=ProcessingState.IDLE; self.config=None; self.optimizer=None
        self.runs=[]; self.result=None; self.comparison=None; self.current_execution=0
        self.message=""; self._phase=""

    def start(self, config):
        config.validate(); self.clear(); self.config=config; self.state=ProcessingState.RUNNING
        # O prefixo também tolera terminais Windows que substituem acentos ao
        # fornecer parâmetros, sem alterar os textos em português da interface.
        self._phase = "nearest" if config.algorithm.startswith("Vizinho Mais") else "genetic"
        self._start_run()

    def _start_run(self):
        is_nearest = self._phase == "nearest"
        self.current_execution += 1
        seed = None if is_nearest else ((self.config.random_seed + self.current_execution-1) if self.config.random_seed is not None else secrets.randbits(32))
        cfg = replace(self.config, random_seed=seed)
        self.optimizer = NearestNeighborOptimizer() if is_nearest else GeneticOptimizer()
        self.optimizer.initialize(self.cities, cfg); self._seed=seed; self._started=time.perf_counter()

    def step(self, amount=1):
        if self.state != ProcessingState.RUNNING: return
        for _ in range(amount):
            self.optimizer.step()
            if self.optimizer.is_finished():
                self.runs.append(RunResult(self.current_execution, self.optimizer.get_best_route(), self.optimizer.get_best_fitness(), list(self.optimizer.get_history()), time.perf_counter()-self._started, self._seed))
                if self._phase == "genetic" and self.current_execution < self.config.executions:
                    self._start_run(); continue
                completed = consolidate("Algoritmo Genético" if self._phase=="genetic" else "Vizinho Mais Próximo", self.runs)
                if self.config.algorithm == "Comparar ambos" and self._phase == "genetic":
                    self._genetic_result=completed; self.runs=[]; self.current_execution=0; self._phase="nearest"; self._start_run(); continue
                if self.config.algorithm == "Comparar ambos":
                    diff=abs(completed.best_run.best_fitness-self._genetic_result.best_run.best_fitness)
                    pct=improvement_percentage(self._genetic_result.best_run.best_fitness, completed.best_run.best_fitness)
                    self.comparison=ComparisonResult(self._genetic_result, completed, diff, pct); self.result=self._genetic_result
                else: self.result=completed
                if self.config.algorithm.startswith("Vizinho Mais") and self.config.executions>1: self.message="O Vizinho Mais Próximo é determinístico e foi executado uma vez."
                self.state=ProcessingState.FINISHED; break

    def pause(self):
        if self.state==ProcessingState.RUNNING: self.state=ProcessingState.PAUSED
    def resume(self):
        if self.state==ProcessingState.PAUSED: self.state=ProcessingState.RUNNING
    def cancel(self):
        if self.state in (ProcessingState.RUNNING, ProcessingState.PAUSED): self.state=ProcessingState.CANCELLED

    @property
    def best_route(self):
        return self.optimizer.get_best_route() if self.optimizer else []
    @property
    def best_fitness(self):
        return self.optimizer.get_best_fitness() if self.optimizer else float("inf")
    @property
    def history(self):
        return self.optimizer.get_history() if self.optimizer else []
