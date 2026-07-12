"""Modelos imutáveis de entrada e modelos de resultado."""
from dataclasses import dataclass
from enum import Enum


class ProcessingState(Enum):
    IDLE="idle"; RUNNING="running"; PAUSED="paused"; FINISHED="finished"; CANCELLED="cancelled"; ERROR="error"

class ProblemType(Enum): TSP="tsp"; HOSPITAL="hospital"
class AlgorithmMode(Enum): GENETIC="genetic"; HEURISTIC="heuristic"; COMPARE="compare"


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

@dataclass(frozen=True)
class ExperimentRequest:
    problem_type: ProblemType; algorithm_mode: AlgorithmMode; execution_config: ExecutionConfig
    tsp_cities: tuple | None=None; hospital_scenario: object | None=None
    def validate(self):
        self.execution_config.validate()
        if self.problem_type is ProblemType.TSP and (not self.tsp_cities or self.hospital_scenario is not None): raise ValueError("TSP exige somente tsp_cities")
        if self.problem_type is ProblemType.HOSPITAL and (self.hospital_scenario is None or self.tsp_cities is not None): raise ValueError("Hospital exige somente hospital_scenario")

@dataclass(frozen=True)
class HospitalGenerationMetric:
    generation:int; objective_cost:float; total_distance_km:float; total_delay_minutes:float; unassigned_count:int; vehicles_used:int
@dataclass(frozen=True)
class HospitalRunResult:
    execution_number:int; seed:int|None; chromosome:tuple; solution:object; history:tuple; elapsed_seconds:float; is_partial:bool=False
@dataclass(frozen=True)
class HospitalExperimentResult:
    algorithm:str; runs:tuple; best_run:HospitalRunResult; average_objective_cost:float; worst_objective_cost:float; standard_deviation:float; average_elapsed_seconds:float
@dataclass(frozen=True)
class HospitalComparisonResult:
    genetic:HospitalExperimentResult; heuristic:HospitalExperimentResult; objective_difference:float; improvement_percentage:float
    distance_difference_km:float; delay_difference_minutes:float; unassigned_difference:int
@dataclass(frozen=True)
class RunnerSnapshot:
    state:ProcessingState; problem_type:ProblemType|None; algorithm_mode:AlgorithmMode|None; current_phase:str
    current_execution:int; total_executions:int; current_generation:int; total_generations:int
    current_best_cost:float|None; global_best_cost:float|None; elapsed_seconds:float; message:str
    partial_result:object|None; final_result:object|None
