"""Exportação estável de resultados hospitalares."""
import csv,json,logging
from dataclasses import asdict,is_dataclass
from datetime import datetime,timezone
from enum import Enum
from pathlib import Path
from scenarios.loader import scenario_to_dict
log=logging.getLogger(__name__)
CSV_FIELDS="timestamp problem_type scenario_id algorithm execution_number population_size generations mutation_probability elite_count seed objective_cost total_distance_km total_duration_minutes total_delay_minutes vehicles_used delivered_count unassigned_count elapsed_seconds is_partial".split()
def _value(value):
    if isinstance(value,Enum):return value.value
    if is_dataclass(value):return {k:_value(v) for k,v in asdict(value).items()}
    if isinstance(value,(list,tuple)):return [_value(x) for x in value]
    if isinstance(value,dict):return {k:_value(v) for k,v in value.items()}
    return value
def export_hospital_json(scenario,algorithm,config,run,results_dir="results"):
    root=Path(results_dir);root.mkdir(parents=True,exist_ok=True); now=datetime.now(timezone.utc); solution=run.solution
    payload={"schema_version":"1.0","exported_at":now.isoformat(),"scenario":scenario_to_dict(scenario),"algorithm":algorithm,"configuration":_value(config),"is_partial":run.is_partial,
      "summary":{"objective_cost":solution.objective_cost,"total_distance_km":solution.total_distance_km,"total_duration_minutes":solution.total_duration_minutes,"total_delay_minutes":solution.total_delay_minutes,"vehicles_used":sum(bool(r.stops) for r in solution.routes),"delivered_count":sum(len(r.stops) for r in solution.routes),"unassigned_count":len(solution.unassigned_deliveries),"elapsed_seconds":run.elapsed_seconds,"seed":run.seed},
      "routes":_value(solution.routes),"unassigned_deliveries":_value(solution.unassigned_deliveries)}
    base=root/f"hospital_solution_{now.strftime('%Y%m%d_%H%M%S_%f')}.json"; base.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8");log.info("JSON exportado: %s",base);return base
def append_experiment_csv(scenario,algorithm,config,run,results_dir="results"):
    root=Path(results_dir);root.mkdir(parents=True,exist_ok=True);path=root/"experiments.csv";s=run.solution
    row={"timestamp":datetime.now(timezone.utc).isoformat(),"problem_type":"hospital","scenario_id":scenario.id,"algorithm":algorithm,"execution_number":run.execution_number,"population_size":config.population_size,"generations":config.generations,"mutation_probability":config.mutation_probability,"elite_count":config.elite_count,"seed":run.seed,"objective_cost":s.objective_cost,"total_distance_km":s.total_distance_km,"total_duration_minutes":s.total_duration_minutes,"total_delay_minutes":s.total_delay_minutes,"vehicles_used":sum(bool(r.stops) for r in s.routes),"delivered_count":sum(len(r.stops) for r in s.routes),"unassigned_count":len(s.unassigned_deliveries),"elapsed_seconds":run.elapsed_seconds,"is_partial":run.is_partial}
    exists=path.exists() and path.stat().st_size>0
    with path.open("a",encoding="utf-8",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=CSV_FIELDS); 
        if not exists:writer.writeheader()
        writer.writerow(row)
    return path
