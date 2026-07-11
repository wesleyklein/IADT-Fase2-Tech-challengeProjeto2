from execution import ExecutionConfig, ExperimentRunner, ProcessingState

CITIES=[(0,0),(2,0),(2,2),(0,2)]
def cfg(algorithm="Algoritmo Genético", executions=2): return ExecutionConfig(algorithm,8,3,executions,.1,1,42)

def finish(runner):
    while runner.state==ProcessingState.RUNNING: runner.step(20)

def test_state_transitions_and_restart():
    runner=ExperimentRunner(CITIES); assert runner.state==ProcessingState.IDLE
    runner.start(cfg()); assert runner.state==ProcessingState.RUNNING
    runner.pause(); assert runner.state==ProcessingState.PAUSED
    runner.resume(); runner.cancel(); assert runner.state==ProcessingState.CANCELLED
    runner.start(cfg(executions=1)); finish(runner); assert runner.state==ProcessingState.FINISHED
    runner.start(cfg(executions=1)); assert runner.state==ProcessingState.RUNNING

def test_multiple_runs_are_consolidated_and_reproducible():
    runner=ExperimentRunner(CITIES); runner.start(cfg()); finish(runner)
    assert len(runner.result.runs)==2 and [r.seed for r in runner.result.runs]==[42,43]

def test_nearest_runs_once_and_comparison_finishes():
    runner=ExperimentRunner(CITIES); runner.start(cfg("Vizinho Mais Próximo",4)); finish(runner)
    assert len(runner.result.runs)==1 and "uma vez" in runner.message
    runner.start(cfg("Comparar ambos",2)); finish(runner)
    assert runner.comparison and runner.comparison.genetic.runs and len(runner.comparison.nearest.runs)==1
