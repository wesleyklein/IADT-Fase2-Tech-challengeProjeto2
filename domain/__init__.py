"""Modelos imutáveis do roteamento hospitalar."""
from dataclasses import dataclass
from enum import Enum, IntEnum
import math

class DeliveryPriority(IntEnum):
    REGULAR = 1
    HIGH = 3
    CRITICAL = 5

def _positive(value, name):
    if not math.isfinite(value) or value <= 0: raise ValueError(f"{name} deve ser positivo e finito")

def _coordinate(value, name):
    if not math.isfinite(value): raise ValueError(f"{name} deve ser finito")

@dataclass(frozen=True)
class Depot:
    id: str; name: str; x_km: float; y_km: float
    def __post_init__(self):
        if not self.id.strip() or not self.name.strip(): raise ValueError("Depósito deve possuir id e nome")
        _coordinate(self.x_km,"x_km"); _coordinate(self.y_km,"y_km")

@dataclass(frozen=True)
class Delivery:
    id: int; name: str; x_km: float; y_km: float; weight_kg: float
    priority: DeliveryPriority; service_time_minutes: float; deadline_minutes: float
    def __post_init__(self):
        if not self.name.strip(): raise ValueError("Entrega deve possuir nome")
        _coordinate(self.x_km,"x_km"); _coordinate(self.y_km,"y_km"); _positive(self.weight_kg,"weight_kg")
        if not math.isfinite(self.service_time_minutes) or self.service_time_minutes < 0: raise ValueError("service_time_minutes deve ser não negativo")
        _positive(self.deadline_minutes,"deadline_minutes")

@dataclass(frozen=True)
class Vehicle:
    id: int; name: str; capacity_kg: float; autonomy_km: float; average_speed_kmh: float
    def __post_init__(self):
        if not self.name.strip(): raise ValueError("Veículo deve possuir nome")
        _positive(self.capacity_kg,"capacity_kg"); _positive(self.autonomy_km,"autonomy_km"); _positive(self.average_speed_kmh,"average_speed_kmh")

@dataclass(frozen=True)
class HospitalScenario:
    id: str; name: str; depot: Depot; deliveries: tuple[Delivery,...]; vehicles: tuple[Vehicle,...]
    def __post_init__(self):
        if not self.id.strip() or not self.name.strip(): raise ValueError("Cenário deve possuir id e nome")
        if not self.deliveries: raise ValueError("Cenário deve possuir entregas")
        if not self.vehicles: raise ValueError("Cenário deve possuir veículos")
        if len({x.id for x in self.deliveries}) != len(self.deliveries): raise ValueError("IDs de entrega duplicados")
        if len({x.id for x in self.vehicles}) != len(self.vehicles): raise ValueError("IDs de veículo duplicados")

@dataclass(frozen=True)
class RouteStop:
    delivery: Delivery; sequence: int; arrival_time_minutes: float; service_start_minutes: float
    departure_time_minutes: float; cumulative_distance_km: float; cumulative_load_kg: float
    is_late: bool; delay_minutes: float

@dataclass(frozen=True)
class VehicleRoute:
    vehicle: Vehicle; stops: tuple[RouteStop,...]; total_distance_km: float; total_load_kg: float
    total_duration_minutes: float; capacity_excess_kg: float; autonomy_excess_km: float

class UnassignedReason(Enum):
    EXCEEDS_ALL_VEHICLE_CAPACITIES="exceeds_all_vehicle_capacities"
    EXCEEDS_ALL_VEHICLE_AUTONOMIES="exceeds_all_vehicle_autonomies"
    NO_FEASIBLE_INSERTION="no_feasible_insertion"
    INVALID_DATA="invalid_data"

@dataclass(frozen=True)
class UnassignedDelivery:
    delivery: Delivery; reason: UnassignedReason; details: str

@dataclass(frozen=True)
class HospitalRoutingSolution:
    chromosome: tuple[int,...]; routes: tuple[VehicleRoute,...]; unassigned_deliveries: tuple[UnassignedDelivery,...]
    total_distance_km: float; total_duration_minutes: float; total_delay_minutes: float
    total_priority_cost: float; total_delay_penalty: float; total_capacity_penalty: float
    total_autonomy_penalty: float; total_unassigned_penalty: float; total_balance_penalty: float
    objective_cost: float; is_feasible: bool
