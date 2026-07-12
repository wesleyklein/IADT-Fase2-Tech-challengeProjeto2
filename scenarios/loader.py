"""Carregamento e validação de cenários JSON, sem dependência gráfica."""
import json
from pathlib import Path
from domain import DeliveryPriority, Depot, Delivery, Vehicle, HospitalScenario

DATA_DIR=Path(__file__).with_name("data")
def list_scenarios(): return sorted(DATA_DIR.glob("*.json"))
def load_scenario(path):
    try: data=json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError,json.JSONDecodeError) as exc: raise ValueError(f"Não foi possível carregar o cenário: {exc}") from exc
    try:
        depot=Depot(**data["depot"])
        deliveries=tuple(Delivery(priority=DeliveryPriority[x.pop("priority")],**x) for x in (dict(v) for v in data["deliveries"]))
        vehicles=tuple(Vehicle(**x) for x in data["vehicles"])
        return HospitalScenario(data["id"],data["name"],depot,deliveries,vehicles)
    except (KeyError,TypeError,ValueError) as exc: raise ValueError(f"Cenário inválido: {exc}") from exc
