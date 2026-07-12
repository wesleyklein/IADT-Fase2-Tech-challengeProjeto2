"""Renderer independente dos cálculos de domínio hospitalar."""
import pygame
from domain import DeliveryPriority
class ViewportTransform:
    def __init__(self,points,rect,margin=35):
        xs=[p[0] for p in points] or [0];ys=[p[1] for p in points] or [0];self.minx=min(xs);self.miny=min(ys)
        dx=max(max(xs)-self.minx,1.);dy=max(max(ys)-self.miny,1.);scale=min((rect.width-2*margin)/dx,(rect.height-2*margin)/dy)
        self.scale=scale;self.left=rect.left+margin;self.bottom=rect.bottom-margin
    def to_screen(self,x,y):return round(self.left+(x-self.minx)*self.scale),round(self.bottom-(y-self.miny)*self.scale)
COLORS=((37,99,235),(234,88,12),(22,163,74),(147,51,234),(14,116,144))
def vehicle_color(index):
    if index<len(COLORS):return COLORS[index]
    return ((index*83)%190+35,(index*137)%190+35,(index*53)%190+35)
def draw_hospital_solution(screen,scenario,solution,rect,font,vehicle_id=None):
    points=[(scenario.depot.x_km,scenario.depot.y_km)]+[(d.x_km,d.y_km) for d in scenario.deliveries];t=ViewportTransform(points,rect)
    depot=t.to_screen(scenario.depot.x_km,scenario.depot.y_km);pygame.draw.rect(screen,(15,23,42),pygame.Rect(depot[0]-8,depot[1]-8,16,16),border_radius=2)
    for i,route in enumerate(solution.routes):
        if vehicle_id is not None and route.vehicle.id!=vehicle_id:continue
        path=[depot]+[t.to_screen(s.delivery.x_km,s.delivery.y_km) for s in route.stops]+[depot]
        if len(path)>2:pygame.draw.lines(screen,vehicle_color(i),False,path,3)
        for stop in route.stops:
            text=font.render(str(stop.sequence),True,(0,0,0));p=t.to_screen(stop.delivery.x_km,stop.delivery.y_km);screen.blit(text,text.get_rect(center=p))
    labels={DeliveryPriority.CRITICAL:"C",DeliveryPriority.HIGH:"A",DeliveryPriority.REGULAR:"R"}
    unassigned={x.delivery.id for x in solution.unassigned_deliveries}
    for d in scenario.deliveries:
        p=t.to_screen(d.x_km,d.y_km);pygame.draw.circle(screen,(220,38,38) if d.id in unassigned else (255,255,255),p,10);pygame.draw.circle(screen,(30,41,59),p,10,2);screen.blit(font.render(labels[d.priority],True,(15,23,42)),(p[0]-5,p[1]-8))
    legend=["H = Hospital   C = Crítica   A = Alta   R = Regular","Vermelho = não atendida"]
    legend += [f"{route.vehicle.name}" for route in solution.routes if route.stops]
    for i,text_value in enumerate(legend):
        color=(15,23,42) if i<2 else vehicle_color(i-2)
        screen.blit(font.render(text_value,True,color),(rect.left+12,rect.top+10+i*20))
