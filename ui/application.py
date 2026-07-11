"""Aplicação desktop interativa para executar e comparar os algoritmos."""
import time

import pygame
import pygame_gui

from benchmark_att48 import att_48_cities_locations
from draw_functions import create_plot_surface, draw_cities, draw_paths, draw_text
from execution import ExecutionConfig, ExperimentRunner, ProcessingState

WIDTH, HEIGHT = 1500, 850
GENERATIONS_PER_FRAME = 10
ALGORITHMS = ["Algoritmo Genético", "Vizinho Mais Próximo", "Comparar ambos"]


def _scaled_cities(cities):
    """Ajusta o ATT48 à região central sem alterar distâncias usadas no cálculo."""
    left, top, width, height = 430, 55, 730, 735
    min_x=min(x for x,_ in cities); max_x=max(x for x,_ in cities)
    min_y=min(y for _,y in cities); max_y=max(y for _,y in cities)
    return [(left+(x-min_x)/(max_x-min_x)*width, top+(y-min_y)/(max_y-min_y)*height) for x,y in cities]


class Application:
    """Mantém separadas a vida da janela e a vida do processamento."""
    def __init__(self):
        pygame.init(); pygame.display.set_caption("Comparador de algoritmos TSP — ATT48")
        self.screen=pygame.display.set_mode((WIDTH, HEIGHT)); self.manager=pygame_gui.UIManager((WIDTH, HEIGHT))
        self.clock=pygame.time.Clock(); self.font=pygame.font.SysFont("Arial", 17)
        self.cities=list(att_48_cities_locations); self.display_cities=_scaled_cities(self.cities)
        self.runner=ExperimentRunner(self.cities); self.plot=None; self.plot_generation=-1; self.started_at=None
        self._build_controls()

    def _label(self, text, y):
        pygame_gui.elements.UILabel(pygame.Rect(15,y,145,30), text, self.manager)

    def _entry(self, value, y):
        entry=pygame_gui.elements.UITextEntryLine(pygame.Rect(165,y,225,30), self.manager)
        entry.set_text(value); return entry

    def _build_controls(self):
        self._label("Algoritmo", 20)
        self.algorithm=pygame_gui.elements.UIDropDownMenu(ALGORITHMS, ALGORITHMS[0], pygame.Rect(165,20,225,35), self.manager)
        fields=[("População","100"),("Gerações","500"),("Execuções","3"),("Mutação","0.10"),("Elitismo","1"),("Semente","")]
        self.entries={}
        for i,(name,value) in enumerate(fields):
            y=70+i*42; self._label(name,y); self.entries[name]=self._entry(value,y)
        labels=[("Processar",15,340),("Pausar",145,340),("Continuar",275,340),("Cancelar",15,385),("Limpar resultados",210,385)]
        self.buttons={name:pygame_gui.elements.UIButton(pygame.Rect(x,y,120 if name!="Limpar resultados" else 180,35),name,self.manager) for name,x,y in labels}
        self.route_choice=pygame_gui.elements.UIDropDownMenu(["Algoritmo Genético","Vizinho Mais Próximo"],"Algoritmo Genético",pygame.Rect(1180,20,285,35),self.manager)

    def _config(self):
        def integer(name): return int(self.entries[name].get_text())
        seed=self.entries["Semente"].get_text().strip()
        return ExecutionConfig(self.algorithm.selected_option, integer("População"), integer("Gerações"), integer("Execuções"), float(self.entries["Mutação"].get_text().replace(",",".")), integer("Elitismo"), int(seed) if seed else None)

    def _click(self, button):
        try:
            if button==self.buttons["Processar"]:
                self.runner.start(self._config()); self.started_at=time.perf_counter(); self.plot=None; self.plot_generation=-1
            elif button==self.buttons["Pausar"]: self.runner.pause(); self._refresh_plot(True)
            elif button==self.buttons["Continuar"]: self.runner.resume()
            elif button==self.buttons["Cancelar"]: self.runner.cancel(); self._refresh_plot(True)
            elif button==self.buttons["Limpar resultados"]: self.runner.clear(); self.plot=None; self.started_at=None
        except (ValueError, TypeError) as error:
            self.runner.state=ProcessingState.ERROR; self.runner.message=str(error)

    def _refresh_plot(self, force=False):
        history=self.runner.history
        if history and (force or len(history)-self.plot_generation>=10):
            self.plot=create_plot_surface(range(1,len(history)+1),history,(285,230)); self.plot_generation=len(history)

    def _route(self):
        route=self.runner.best_route
        if self.runner.comparison:
            result=self.runner.comparison.nearest if self.route_choice.selected_option=="Vizinho Mais Próximo" else self.runner.comparison.genetic
            route=result.best_run.best_route
        index={city:i for i,city in enumerate(self.cities)}
        return [self.display_cities[index[city]] for city in route]

    def _lines(self):
        state_names={"idle":"Aguardando","running":"Processando","paused":"Pausado","finished":"Concluído","cancelled":"Cancelado","error":"Erro"}
        lines=[f"Status: {state_names[self.runner.state.value]}"]
        if self.runner.config:
            total=1 if self.runner._phase=="nearest" else self.runner.config.executions
            gen=getattr(self.runner.optimizer,"generation",1 if self.runner.optimizer and self.runner.optimizer.is_finished() else 0)
            lines += [f"Execução: {self.runner.current_execution} de {total}",f"Geração: {gen} de {self.runner.config.generations}"]
        if self.runner.best_fitness != float("inf"): lines.append(f"Melhor atual: {self.runner.best_fitness:,.2f}")
        if self.started_at: lines.append(f"Tempo decorrido: {time.perf_counter()-self.started_at:.2f} s")
        if self.runner.result:
            r=self.runner.result
            lines += ["",f"Melhor distância: {r.best_run.best_fitness:,.2f}",f"Distância média: {r.average_fitness:,.2f}",f"Pior distância: {r.worst_fitness:,.2f}",f"Desvio-padrão: {r.standard_deviation:,.2f}",f"Tempo médio: {r.average_elapsed_seconds:.2f} s",f"Melhor execução: {r.best_run.execution_number}"]
        if self.runner.comparison:
            c=self.runner.comparison; lines += ["","COMPARAÇÃO",f"Genético: {c.genetic.best_run.best_fitness:,.2f}",f"Vizinho: {c.nearest.best_run.best_fitness:,.2f}",f"Diferença: {c.absolute_difference:,.2f}",f"Melhoria do AG: {c.improvement_percentage:.2f}%"]
            if c.improvement_percentage<0: lines.append("O AG encontrou uma solução pior.")
        if self.runner.message: lines += ["",self.runner.message]
        return lines

    def draw(self):
        self.screen.fill((245,247,250)); pygame.draw.rect(self.screen,(255,255,255),(410,20,770,810)); pygame.draw.rect(self.screen,(255,255,255),(1170,70,315,760))
        route=self._route()
        if route: draw_paths(self.screen,route,(37,99,235),3)
        draw_cities(self.screen,self.display_cities,(220,38,38),5)
        if self.plot: self.screen.blit(self.plot,(1185,575))
        for i,line in enumerate(self._lines()): draw_text(self.screen,line,(25,30,40),(1190,85+i*25),self.font)
        self.manager.draw_ui(self.screen); pygame.display.flip()

    def run(self):
        application_running=True
        while application_running:
            delta=self.clock.tick(60)/1000
            for event in pygame.event.get():
                if event.type==pygame.QUIT or (event.type==pygame.KEYDOWN and event.key in (pygame.K_q,pygame.K_ESCAPE)): application_running=False
                if event.type==pygame_gui.UI_BUTTON_PRESSED: self._click(event.ui_element)
                self.manager.process_events(event)
            self.runner.step(GENERATIONS_PER_FRAME); self._refresh_plot(self.runner.state in (ProcessingState.FINISHED,ProcessingState.CANCELLED))
            self.manager.update(delta); self.draw()
        pygame.quit()


def run_application():
    """Inicia a aplicação; ponto público compartilhado por app.py e tsp.py."""
    Application().run()
