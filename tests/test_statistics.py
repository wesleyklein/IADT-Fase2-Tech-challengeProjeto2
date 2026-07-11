import pytest
from execution.models import RunResult
from execution.statistics import consolidate, improvement_percentage

def run(number,fitness,time=.5): return RunResult(number,[],fitness,[],time,None)
def test_statistics_for_multiple_runs():
    result=consolidate("AG",[run(1,10),run(2,20)])
    assert result.best_run.execution_number==1 and result.average_fitness==15 and result.worst_fitness==20
    assert result.standard_deviation==pytest.approx(7.0710678) and result.average_elapsed_seconds==.5
def test_single_run_has_zero_deviation(): assert consolidate("AG",[run(1,10)]).standard_deviation==0
def test_improvement_percentage():
    assert improvement_percentage(90,100)==10
    assert improvement_percentage(110,100)==-10
