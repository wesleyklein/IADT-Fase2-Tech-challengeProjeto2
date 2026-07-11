"""Modelos imutáveis de entrada e modelos de resultado."""
from dataclasses import dataclass
from enum import Enum


class ProcessingState(Enum):
    IDLE="idle"; RUNNING="running"; PAUSED="paused"; FINISHED="finished"; CANCELLED="cancelled"; ERROR="error"


@dataclass(frozen=True)
class ExecutionConfig:
    algorithm: str = "Algoritmo Genético"
    population_size: int = 100
    generations: int = 500
    executions: int = 3
    mutation_probability: float = .10
    elite_count: int = 1
    random_seed: int | None = None

    def validate(self) -> None:
        if not 2 <= self.population_size <= 10_000: raise ValueError("A população deve estar entre 2 e 10.000.")
        if not 1 <= self.generations <= 100_000: raise ValueError("As gerações devem estar entre 1 e 100.000.")
        if not 1 <= self.executions <= 1_000: raise ValueError("As execuções devem estar entre 1 e 1.000.")
        if not 0 <= self.mutation_probability <= 1: raise ValueError("A mutação deve estar entre 0 e 1.")
        if not 1 <= self.elite_count < self.population_size: raise ValueError("A quantidade de elites deve ser menor que a população.")


@dataclass
class RunResult:
    execution_number: int; best_route: list; best_fitness: float
    fitness_history: list[float]; elapsed_seconds: float; seed: int | None


@dataclass
class ExperimentResult:
    algorithm: str; runs: list[RunResult]; best_run: RunResult
    average_fitness: float; worst_fitness: float; standard_deviation: float
    average_elapsed_seconds: float


@dataclass
class ComparisonResult:
    genetic: ExperimentResult; nearest: ExperimentResult
    absolute_difference: float; improvement_percentage: float
