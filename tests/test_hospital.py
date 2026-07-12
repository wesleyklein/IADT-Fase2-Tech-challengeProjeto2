import json
import pytest
from domain import *
from routing import *
from scenarios import load_scenario

def scenario():
    return HospitalScenario("x","Teste",Depot("d","Hospital",0,0),(
        Delivery(1,"Crítica",3,4,5,DeliveryPriority.CRITICAL,10,5),
        Delivery(2,"Regular",6,0,5,DeliveryPriority.REGULAR,0,100),),
        (Vehicle(1,"Van",20,30,60),))

def test_distance_time_and_validation():
    assert euclidean_distance_km(0,0,3,4)==5 and travel_time_minutes(10,60)==10
    with pytest.raises(ValueError): Vehicle(1,"",0,1,1)

def test_decoder_preserves_input_and_return_distance():
    chromosome=[1,2]; result=HospitalRouteDecoder().decode(chromosome,scenario())
    assert chromosome==[1,2] and result.is_feasible and result.routes[0].total_distance_km>11
    assert [s.delivery.id for s in result.routes[0].stops]==chromosome

def test_invalid_chromosome_rejected():
    with pytest.raises(ValueError): HospitalRouteDecoder().decode([1,1],scenario())

def test_impossible_capacity_has_reason():
    s=scenario(); heavy=Delivery(3,"Pesada",1,1,99,DeliveryPriority.REGULAR,0,10)
    s=HospitalScenario("y","Y",s.depot,(heavy,),s.vehicles)
    result=HospitalRouteDecoder().decode([3],s)
    assert result.unassigned_deliveries[0].reason is UnassignedReason.EXCEEDS_ALL_VEHICLE_CAPACITIES

def test_loader_valid_scenario():
    s=load_scenario("scenarios/data/hospital_viavel.json")
    assert len(s.deliveries)==15 and len(s.vehicles)==3
