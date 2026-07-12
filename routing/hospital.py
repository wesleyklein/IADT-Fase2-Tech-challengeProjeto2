"""Decodificação determinística e fitness hospitalar."""
from dataclasses import dataclass
import math, statistics
from domain import *

def euclidean_distance_km(ax, ay, bx, by): return math.hypot(bx-ax, by-ay)
def travel_time_minutes(distance_km, average_speed_kmh):
    if average_speed_kmh <= 0: raise ValueError("Velocidade deve ser positiva")
    return distance_km / average_speed_kmh * 60.0

@dataclass(frozen=True)
class HospitalFitnessWeights:
    distance_weight: float=1.; priority_arrival_weight: float=.2; delay_weight: float=50.
    critical_delay_multiplier: float=5.; high_delay_multiplier: float=3.; regular_delay_multiplier: float=1.
    capacity_excess_weight: float=10_000.; autonomy_excess_weight: float=10_000.
    unassigned_delivery_weight: float=1_000_000.; route_balance_weight: float=2.

class HospitalRouteDecoder:
    def __init__(self, weights=None): self.weights=weights or HospitalFitnessWeights()
    def decode(self, chromosome, scenario):
        ids=[d.id for d in scenario.deliveries]
        if len(chromosome)!=len(ids) or set(chromosome)!=set(ids): raise ValueError("Cromossomo deve ser uma permutação completa e sem duplicações")
        by_id={d.id:d for d in scenario.deliveries}; assigned={v.id:[] for v in scenario.vehicles}; unassigned=[]
        depot=scenario.depot
        def route_distance(stops):
            points=[(depot.x_km,depot.y_km)]+[(d.x_km,d.y_km) for d in stops]+[(depot.x_km,depot.y_km)]
            return sum(euclidean_distance_km(*a,*b) for a,b in zip(points,points[1:]))
        for delivery_id in chromosome:
            d=by_id[delivery_id]
            if all(d.weight_kg>v.capacity_kg for v in scenario.vehicles):
                unassigned.append(UnassignedDelivery(d,UnassignedReason.EXCEEDS_ALL_VEHICLE_CAPACITIES,"Peso excede todas as capacidades")); continue
            roundtrip=2*euclidean_distance_km(depot.x_km,depot.y_km,d.x_km,d.y_km)
            if all(roundtrip>v.autonomy_km for v in scenario.vehicles):
                unassigned.append(UnassignedDelivery(d,UnassignedReason.EXCEEDS_ALL_VEHICLE_AUTONOMIES,"Ida e volta excedem todas as autonomias")); continue
            candidates=[]
            for v in scenario.vehicles:
                current=assigned[v.id]; load=sum(x.weight_kg for x in current)+d.weight_kg
                newdist=route_distance(current+[d])
                if load<=v.capacity_kg and newdist<=v.autonomy_km:
                    inc=newdist-route_distance(current); arrival=travel_time_minutes(newdist/2,v.average_speed_kmh)
                    cost=inc+arrival*int(d.priority)*.2+(load/v.capacity_kg)
                    candidates.append((cost,inc,load/v.capacity_kg,v.id,v))
            if not candidates: unassigned.append(UnassignedDelivery(d,UnassignedReason.NO_FEASIBLE_INSERTION,"Não há inserção viável"))
            else: assigned[min(candidates)[-1].id].append(d)
        routes=[]
        for v in scenario.vehicles:
            current=(depot.x_km,depot.y_km); elapsed=distance=load=0.; stops=[]
            for sequence,d in enumerate(assigned[v.id],1):
                leg=euclidean_distance_km(*current,d.x_km,d.y_km); distance+=leg
                elapsed+=travel_time_minutes(leg,v.average_speed_kmh); arrival=elapsed; delay=max(0.,arrival-d.deadline_minutes)
                load+=d.weight_kg; elapsed+=d.service_time_minutes
                stops.append(RouteStop(d,sequence,arrival,arrival,elapsed,distance,load,delay>0,delay)); current=(d.x_km,d.y_km)
            back=euclidean_distance_km(*current,depot.x_km,depot.y_km) if stops else 0.
            total_distance=distance+back; duration=elapsed+travel_time_minutes(back,v.average_speed_kmh)
            routes.append(VehicleRoute(v,tuple(stops),total_distance,load,duration,max(0.,load-v.capacity_kg),max(0.,total_distance-v.autonomy_km)))
        w=self.weights; total_distance=sum(r.total_distance_km for r in routes); total_duration=sum(r.total_duration_minutes for r in routes)
        priority=sum(s.arrival_time_minutes*int(s.delivery.priority)*w.priority_arrival_weight for r in routes for s in r.stops)
        multipliers={DeliveryPriority.REGULAR:w.regular_delay_multiplier,DeliveryPriority.HIGH:w.high_delay_multiplier,DeliveryPriority.CRITICAL:w.critical_delay_multiplier}
        delay=sum(s.delay_minutes for r in routes for s in r.stops); delay_pen=sum(s.delay_minutes*w.delay_weight*multipliers[s.delivery.priority] for r in routes for s in r.stops)
        cap=sum(r.capacity_excess_kg for r in routes)*w.capacity_excess_weight; auto=sum(r.autonomy_excess_km for r in routes)*w.autonomy_excess_weight
        unas=sum(w.unassigned_delivery_weight*int(x.delivery.priority) for x in unassigned)
        used=[r.total_duration_minutes for r in routes if r.stops]; balance=(statistics.pstdev(used)*w.route_balance_weight if len(used)>1 else 0.)
        objective=total_distance*w.distance_weight+priority+delay_pen+cap+auto+unas+balance
        return HospitalRoutingSolution(tuple(chromosome),tuple(routes),tuple(unassigned),total_distance,total_duration,delay,priority,delay_pen,cap,auto,unas,balance,objective,not unassigned and cap==0 and auto==0)

class HospitalRoutingEvaluator:
    def __init__(self, scenario, weights=None): self.scenario=scenario; self.decoder=HospitalRouteDecoder(weights)
    def evaluate(self, chromosome): return self.decode(chromosome).objective_cost
    def decode(self, chromosome): return self.decoder.decode(chromosome,self.scenario)
