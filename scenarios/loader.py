"""Persistência segura de cenários hospitalares."""
import json, logging, os, re
from dataclasses import asdict, replace
from pathlib import Path
from domain import *

log=logging.getLogger(__name__); DATA_DIR=Path(__file__).with_name("data"); DEFAULT_DIR=DATA_DIR/"default"; USER_DIR=DATA_DIR/"user"
def _id(value):
    if not re.fullmatch(r"[a-zA-Z0-9_-]+",value): raise ValueError("ID de cenário inválido")
    return value
def scenario_from_dict(data):
    try:
        depot=Depot(**data["depot"]); weights=HospitalFitnessWeights(**data.get("fitness_weights",{}))
        deliveries=tuple(Delivery(priority=DeliveryPriority[x.pop("priority")],**x) for x in (dict(v) for v in data["deliveries"]))
        vehicles=tuple(Vehicle(**x) for x in data["vehicles"])
        return HospitalScenario(data["id"],data["name"],depot,deliveries,vehicles,weights)
    except (KeyError,TypeError,ValueError) as exc: raise ValueError(f"Cenário inválido: {exc}") from exc
def scenario_to_dict(s):
    data=asdict(s); data["deliveries"]=[{**asdict(x),"priority":x.priority.name} for x in s.deliveries]; return data
def load_scenario(path):
    path=Path(path)
    if not path.exists() and path.parent.name=="data":path=DEFAULT_DIR/path.name
    try:return scenario_from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError,json.JSONDecodeError) as exc:raise ValueError(f"Não foi possível carregar o cenário: {exc}") from exc
def list_scenarios(): return sorted([*DEFAULT_DIR.glob("*.json"),*USER_DIR.glob("*.json"),*DATA_DIR.glob("*.json")])

class ScenarioRepository:
    def __init__(self,default_dir=DEFAULT_DIR,user_dir=USER_DIR):self.default_dir=Path(default_dir);self.user_dir=Path(user_dir);self.user_dir.mkdir(parents=True,exist_ok=True)
    def list_all(self):return [(p.stem,load_scenario(p).name,p.parent==self.default_dir) for p in sorted([*self.default_dir.glob("*.json"),*self.user_dir.glob("*.json")])]
    def _find(self,scenario_id):
        _id(scenario_id)
        for root in (self.default_dir,self.user_dir):
            p=root/f"{scenario_id}.json"
            if p.exists():return p
        raise KeyError(scenario_id)
    def load(self,scenario_id):return load_scenario(self._find(scenario_id))
    def save(self,scenario,overwrite=False):
        _id(scenario.id)
        if (self.default_dir/f"{scenario.id}.json").exists():raise PermissionError("Cenário padrão é somente leitura")
        target=self.user_dir/f"{scenario.id}.json"
        if target.exists() and not overwrite:raise FileExistsError(target)
        temp=target.with_suffix(".tmp"); temp.write_text(json.dumps(scenario_to_dict(scenario),ensure_ascii=False,indent=2),encoding="utf-8"); os.replace(temp,target); log.info("Cenário salvo: %s",target); return target
    def delete(self,scenario_id):
        path=self._find(scenario_id)
        if path.parent==self.default_dir:raise PermissionError("Cenário padrão não pode ser excluído")
        path.unlink()
    def clone(self,scenario_id,new_id,new_name):return replace(self.load(scenario_id),id=_id(new_id),name=new_name)
