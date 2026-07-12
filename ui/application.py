"""Aplicação desktop interativa para executar e comparar os algoritmos."""
import time

import pygame
import pygame_gui

from benchmark_att48 import att_48_cities_locations
from draw_functions import create_plot_surface, draw_cities, draw_paths, draw_text
from execution import (ExecutionConfig, ExperimentRunner, ProcessingState, ProblemType,
                       AlgorithmMode, ExperimentRequest)
from scenarios import list_scenarios, load_scenario
from ui.hospital_renderer import draw_hospital_solution

WIDTH, HEIGHT = 1500, 850
GENERATIONS_PER_FRAME = 10
ALGORITHMS = ["Algoritmo Genético", "Vizinho Mais Próximo", "Comparar ambos"]
PROBLEM_TYPES=["TSP / ATT48","Hospitalar / VRP"]
ROUTE_GENETIC = "genetic"
ROUTE_NEAREST = "nearest"


def _dropdown_value(dropdown) -> str:
    """Obtém o texto selecionado em diferentes versões do pygame_gui.

    Algumas versões retornam uma string e outras retornam uma tupla contendo
    o texto exibido e um identificador interno.
    """
    selected = dropdown.selected_option
    if isinstance(selected, tuple):
        return str(selected[0])
    return str(selected)


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
        self.runner=ExperimentRunner(); self.plot=None; self.plot_generation=-1
        self.scenario_paths=list_scenarios(); self.current_scenario=load_scenario(self.scenario_paths[0]) if self.scenario_paths else None
        self.selected_route=ROUTE_GENETIC
        self.started_at=None; self.ended_at=None
        self._build_controls()

    def _label(self, text, y):
        pygame_gui.elements.UILabel(pygame.Rect(15,y,145,30), text, self.manager)

    def _entry(self, value, y):
        entry=pygame_gui.elements.UITextEntryLine(pygame.Rect(165,y,225,30), self.manager)
        entry.set_text(value); return entry

    def _build_controls(self):
        self._label("Tipo", 435)
        self.problem_type=pygame_gui.elements.UIDropDownMenu(PROBLEM_TYPES,PROBLEM_TYPES[0],pygame.Rect(165,435,225,35),self.manager)
        scenario_names=[p.stem for p in self.scenario_paths] or ["Nenhum cenário"]
        self._label("Cenário",477)
        self.scenario_dropdown=pygame_gui.elements.UIDropDownMenu(scenario_names,scenario_names[0],pygame.Rect(165,477,225,35),self.manager)
        self._label("Algoritmo", 20)
        self.algorithm=pygame_gui.elements.UIDropDownMenu(ALGORITHMS, ALGORITHMS[0], pygame.Rect(165,20,225,35), self.manager)
        fields=[("População","100"),("Gerações","500"),("Execuções","3"),("Mutação","0.10"),("Elitismo","1"),("Semente","")]
        self.entries={}
        for i,(name,value) in enumerate(fields):
            y=70+i*42; self._label(name,y); self.entries[name]=self._entry(value,y)
        labels=[("Processar",15,340),("Pausar",145,340),("Continuar",275,340),("Cancelar",15,385),("Limpar resultados",210,385)]
        self.buttons={name:pygame_gui.elements.UIButton(pygame.Rect(x,y,120 if name!="Limpar resultados" else 180,35),name,self.manager) for name,x,y in labels}
        self.route_buttons = {
            ROUTE_GENETIC: pygame_gui.elements.UIButton(
                pygame.Rect(1180, 565, 140, 35), "Rota Genética", self.manager
            ),
            ROUTE_NEAREST: pygame_gui.elements.UIButton(
                pygame.Rect(1330, 565, 140, 35), "Rota Vizinho", self.manager
            ),
        }
        self._update_route_buttons()
        # Indicador somente de leitura: o algoritmo ativo é controlado pelo
        # runner, portanto não deve parecer uma opção que o usuário precisa
        # alterar durante o processamento.
        self.processing_algorithm_label=pygame_gui.elements.UILabel(
            pygame.Rect(1180,20,285,35),
            "Algoritmo: aguardando processamento",
            self.manager,
        )

    def _config(self):
        def integer(name): return int(self.entries[name].get_text())
        seed=self.entries["Semente"].get_text().strip()
        return ExecutionConfig(_dropdown_value(self.algorithm), integer("População"), integer("Gerações"), integer("Execuções"), float(self.entries["Mutação"].get_text().replace(",",".")), integer("Elitismo"), int(seed) if seed else None)

    def _request(self):
        config=self._config(); algorithm=_dropdown_value(self.algorithm)
        mode=AlgorithmMode.COMPARE if algorithm=="Comparar ambos" else (AlgorithmMode.HEURISTIC if algorithm.startswith("Vizinho") else AlgorithmMode.GENETIC)
        if _dropdown_value(self.problem_type)==PROBLEM_TYPES[0]:return ExperimentRequest(ProblemType.TSP,mode,config,tuple(self.cities))
        selected=_dropdown_value(self.scenario_dropdown); path=next(p for p in self.scenario_paths if p.stem==selected);self.current_scenario=load_scenario(path)
        return ExperimentRequest(ProblemType.HOSPITAL,mode,config,hospital_scenario=self.current_scenario)

    def _click(self, button):
        try:
            # Trata primeiro os seletores de rota. A comparação por identidade
            # evita que o pygame_gui confunda elementos com atributos semelhantes.
            if button is self.route_buttons[ROUTE_GENETIC]:
                self._select_route(ROUTE_GENETIC)
            elif button is self.route_buttons[ROUTE_NEAREST]:
                self._select_route(ROUTE_NEAREST)
            elif button==self.buttons["Processar"]:
                self.runner.start(self._request()); self.started_at=time.perf_counter(); self.ended_at=None; self.plot=None; self.plot_generation=-1; self.selected_route=ROUTE_GENETIC
                self._update_route_buttons()
            elif button==self.buttons["Pausar"]: self.runner.pause(); self._refresh_plot(True)
            elif button==self.buttons["Continuar"]: self.runner.resume()
            elif button==self.buttons["Cancelar"]:
                self.runner.cancel(); self._stop_timer(); self._refresh_plot(True)
            elif button==self.buttons["Limpar resultados"]:
                self.runner.clear(); self.plot=None; self.started_at=None; self.ended_at=None; self.selected_route=ROUTE_GENETIC
                self._update_route_buttons()
        except (ValueError, TypeError) as error:
            self.runner.fail(error)

    def _select_route(self, route_name):
        """Seleciona uma das duas rotas consolidadas da comparação."""
        if self.runner.comparison and route_name in (ROUTE_GENETIC, ROUTE_NEAREST):
            self.selected_route=route_name
            self._update_route_buttons()

    def _update_route_buttons(self):
        selected = self.selected_route
        self.route_buttons[ROUTE_GENETIC].set_text(
            "✓ Rota Genética" if selected == ROUTE_GENETIC else "Rota Genética"
        )
        self.route_buttons[ROUTE_NEAREST].set_text(
            "✓ Rota Vizinho" if selected == ROUTE_NEAREST else "Rota Vizinho"
        )

    def _refresh_plot(self, force=False):
        history=self.runner.history
        history_changed = len(history) != self.plot_generation
        periodic_refresh = len(history) - self.plot_generation >= 10
        if history and history_changed and (force or periodic_refresh):
            self.plot=create_plot_surface(range(1,len(history)+1),history,(285,230)); self.plot_generation=len(history)

    def _stop_timer(self):
        """Congela o cronômetro na primeira conclusão ou cancelamento."""
        if self.started_at is not None and self.ended_at is None:
            self.ended_at = time.perf_counter()

    def _route(self):
        route=self.runner.best_route
        if self.runner.comparison:
            result = (self.runner.comparison.nearest
                      if self.selected_route == ROUTE_NEAREST
                      else self.runner.comparison.genetic)
            route=result.best_run.best_route
        index={city:i for i,city in enumerate(self.cities)}
        return [self.display_cities[index[city]] for city in route]

    def _update_algorithm_label(self):
        """Atualiza o texto da direita conforme a fase realmente executada."""
        if self.runner.state == ProcessingState.IDLE:
            text = "Algoritmo: aguardando processamento"
        elif self.runner.state == ProcessingState.ERROR:
            text = "Algoritmo: não iniciado"
        elif self.runner.comparison:
            name = "Vizinho Mais Próximo" if self.selected_route == ROUTE_NEAREST else "Algoritmo Genético"
            text = f"Rota exibida: {name}"
        elif self.runner.get_snapshot().current_phase in ("nearest","heuristic"):
            text = "Processando: Vizinho Mais Próximo"
        else:
            text = "Processando: Algoritmo Genético"
        self.processing_algorithm_label.set_text(text)

    def _lines(self):
        state_names={"idle":"Aguardando","running":"Processando","paused":"Pausado","finished":"Concluído","cancelled":"Cancelado","error":"Erro"}
        lines=[f"Status: {state_names[self.runner.state.value]}"]
        snapshot=self.runner.get_snapshot()
        if self.runner.config: lines += [f"Execução: {snapshot.current_execution} de {snapshot.total_executions}",f"Geração: {snapshot.current_generation} de {snapshot.total_generations}"]
        if self.runner.best_fitness != float("inf"): lines.append(f"Melhor atual: {self.runner.best_fitness:,.2f}")
        if self.started_at:
            timer_end = self.ended_at if self.ended_at is not None else time.perf_counter()
            lines.append(f"Tempo decorrido: {timer_end-self.started_at:.2f} s")
        if self.runner.result:
            r=self.runner.result
            lines += ["",f"Melhor distância: {r.best_run.best_fitness:,.2f}",f"Distância média: {r.average_fitness:,.2f}",f"Pior distância: {r.worst_fitness:,.2f}",f"Desvio-padrão: {r.standard_deviation:,.2f}",f"Tempo médio: {r.average_elapsed_seconds:.2f} s",f"Melhor execução: {r.best_run.execution_number}"]
        if self.runner.comparison:
            c=self.runner.comparison; lines += ["","COMPARAÇÃO",f"Genético: {c.genetic.best_run.best_fitness:,.2f}",f"Vizinho: {c.nearest.best_run.best_fitness:,.2f}",f"Diferença: {c.absolute_difference:,.2f}",f"Melhoria do AG: {c.improvement_percentage:.2f}%"]
            if c.improvement_percentage<0: lines.append("O AG encontrou uma solução pior.")
        if self.runner.message: lines += ["",self.runner.message]
        return lines

    def draw(self):
        self._update_algorithm_label()
        snapshot=self.runner.get_snapshot()
        self.screen.fill((245,247,250)); pygame.draw.rect(self.screen,(255,255,255),(410,20,770,810)); pygame.draw.rect(self.screen,(255,255,255),(1170,70,315,760))
        hospital_solution=self.runner.optimizer.get_best_solution() if snapshot.problem_type is ProblemType.HOSPITAL and self.runner.optimizer else None
        route=[] if hospital_solution else self._route()
        if hospital_solution: draw_hospital_solution(self.screen,self.current_scenario,hospital_solution,pygame.Rect(410,20,770,810),self.font)
        elif route:
            route_color = (234, 88, 12) if self.selected_route == ROUTE_NEAREST and self.runner.comparison else (37,99,235)
            draw_paths(self.screen,route,route_color,3)
        draw_cities(self.screen,self.display_cities,(220,38,38),5)
        if self.plot: self.screen.blit(self.plot,(1185,615))
        for i,line in enumerate(self._lines()): draw_text(self.screen,line,(25,30,40),(1190,85+i*25),self.font)
        self.manager.draw_ui(self.screen); pygame.display.flip()

    def run(self):
        application_running=True
        while application_running:
            delta=self.clock.tick(60)/1000
            for event in pygame.event.get():
                if event.type==pygame.QUIT or (event.type==pygame.KEYDOWN and event.key in (pygame.K_q,pygame.K_ESCAPE)): application_running=False
                is_button_event = (event.type == pygame_gui.UI_BUTTON_PRESSED or
                                   getattr(event, "user_type", None) == pygame_gui.UI_BUTTON_PRESSED)
                if is_button_event: self._click(event.ui_element)
                self.manager.process_events(event)
            self.runner.step(GENERATIONS_PER_FRAME)
            if self.runner.state in (ProcessingState.FINISHED, ProcessingState.CANCELLED, ProcessingState.ERROR):
                self._stop_timer()
            self._refresh_plot(self.runner.state in (ProcessingState.FINISHED,ProcessingState.CANCELLED))
            self.manager.update(delta); self.draw()
        pygame.quit()


def run_application():
    """Inicia a aplicação; ponto público compartilhado por app.py e tsp.py."""
    Application().run()
