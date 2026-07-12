from dataclasses import replace
import json
import pytest
from execution import *
from execution.exporter import export_hospital_json,append_experiment_csv
from scenarios import ScenarioRepository,load_scenario

def config():return ExecutionConfig(population_size=6,generations=2,executions=1,elite_count=1,random_seed=7)
def finish(r):
    while r.state is ProcessingState.RUNNING:r.step(20)

def test_hospital_runner_four_modes_and_snapshot():
    scenario=load_scenario("scenarios/data/default/hospital_viavel.json")
    for mode in (AlgorithmMode.GENETIC,AlgorithmMode.HEURISTIC,AlgorithmMode.COMPARE):
        r=ExperimentRunner();r.start(ExperimentRequest(ProblemType.HOSPITAL,mode,config(),hospital_scenario=scenario));finish(r)
        assert r.state is ProcessingState.FINISHED and r.get_snapshot().final_result

def test_cancel_preserves_hospital_partial():
    scenario=load_scenario("scenarios/data/default/hospital_viavel.json");r=ExperimentRunner();r.start(ExperimentRequest(ProblemType.HOSPITAL,AlgorithmMode.GENETIC,replace(config(),generations=20),hospital_scenario=scenario));r.step();r.cancel()
    assert r.get_snapshot().partial_result.is_partial

def test_repository_security_clone_save_delete(tmp_path):
    default=tmp_path/"default";user=tmp_path/"user";default.mkdir();s=load_scenario("scenarios/data/default/hospital_viavel.json")
    repo=ScenarioRepository(default,user);clone=replace(s,id="clone",name="Clone");repo.save(clone);assert repo.load("clone").name=="Clone";repo.delete("clone")
    with pytest.raises(ValueError):repo.load("../escape")

def test_exports_json_and_single_csv_header(tmp_path):
    scenario=load_scenario("scenarios/data/default/hospital_viavel.json");r=ExperimentRunner();r.start(ExperimentRequest(ProblemType.HOSPITAL,AlgorithmMode.HEURISTIC,config(),hospital_scenario=scenario));finish(r);run=r.result.best_run
    path=export_hospital_json(scenario,"heuristic",config(),run,tmp_path);assert json.loads(path.read_text(encoding="utf-8"))["schema_version"]=="1.0"
    csv=append_experiment_csv(scenario,"heuristic",config(),run,tmp_path);append_experiment_csv(scenario,"heuristic",config(),run,tmp_path);assert csv.read_text(encoding="utf-8").count("timestamp")==1

def test_generation_metrics_are_recorded_by_optimizer():
    scenario=load_scenario("scenarios/data/default/hospital_viavel.json");r=ExperimentRunner();r.start(ExperimentRequest(ProblemType.HOSPITAL,AlgorithmMode.GENETIC,replace(config(),generations=4),hospital_scenario=scenario));finish(r)
    metrics=r.result.best_run.history
    assert [x.generation for x in metrics]==[1,2,3,4]
    assert len(metrics)==4 and all(x.objective_cost>0 for x in metrics)

def test_high_demand_has_required_size_and_fleet():
    scenario=load_scenario("scenarios/data/default/hospital_alta_demanda.json")
    assert 30<=len(scenario.deliveries)<=50 and 4<=len(scenario.vehicles)<=6

def test_display_solution_selects_both_comparison_results():
    scenario=load_scenario("scenarios/data/default/hospital_viavel.json");r=ExperimentRunner();r.start(ExperimentRequest(ProblemType.HOSPITAL,AlgorithmMode.COMPARE,config(),hospital_scenario=scenario));finish(r)
    assert r.get_display_solution("genetic") is r.comparison.genetic.best_run.solution
    assert r.get_display_solution("heuristic") is r.comparison.heuristic.best_run.solution
