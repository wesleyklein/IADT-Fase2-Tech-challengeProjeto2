"""Importadores CSV transacionais."""
import csv
from domain import Delivery,DeliveryPriority,Vehicle
def _rows(path):
    with open(path,encoding="utf-8-sig",newline="") as stream:return list(csv.DictReader(stream))
def import_vehicles_csv(path):
    result=[]
    for line,row in enumerate(_rows(path),2):
        try:result.append(Vehicle(int(row["id"]),row["name"],float(row["capacity_kg"]),float(row["autonomy_km"]),float(row["average_speed_kmh"])))
        except Exception as exc:raise ValueError(f"Linha {line}: {exc}") from exc
    if len({x.id for x in result})!=len(result):raise ValueError("IDs de veículo duplicados")
    return tuple(result)
def import_deliveries_csv(path):
    result=[]
    for line,row in enumerate(_rows(path),2):
        try:result.append(Delivery(int(row["id"]),row["name"],float(row["x_km"]),float(row["y_km"]),float(row["weight_kg"]),DeliveryPriority[row["priority"]],float(row["service_time_minutes"]),float(row["deadline_minutes"])))
        except Exception as exc:raise ValueError(f"Linha {line}: {exc}") from exc
    if len({x.id for x in result})!=len(result):raise ValueError("IDs de entrega duplicados")
    return tuple(result)
