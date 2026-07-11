"""Consolidação estatística de resultados."""
import statistics
from .models import ExperimentResult


def consolidate(algorithm, runs):
    values = [run.best_fitness for run in runs]
    return ExperimentResult(algorithm, list(runs), min(runs, key=lambda r: r.best_fitness), statistics.mean(values), max(values), statistics.stdev(values) if len(values)>1 else 0.0, statistics.mean(r.elapsed_seconds for r in runs))


def improvement_percentage(genetic_distance, nearest_distance):
    return 0.0 if nearest_distance == 0 else (nearest_distance-genetic_distance)/nearest_distance*100
