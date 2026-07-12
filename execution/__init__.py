"""Controle e resultados de experimentos."""
from .models import ExecutionConfig, ProcessingState, ProblemType, AlgorithmMode, ExperimentRequest, RunnerSnapshot
from .experiment_runner import ExperimentRunner

__all__ = ["ExecutionConfig", "ProcessingState", "ProblemType", "AlgorithmMode", "ExperimentRequest", "RunnerSnapshot", "ExperimentRunner"]
