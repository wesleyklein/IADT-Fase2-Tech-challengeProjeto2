"""Aplicação desktop interativa para executar e comparar os algoritmos."""
import time

import pygame
import pygame_gui

from benchmark_att48 import att_48_cities_locations
from draw_functions import create_plot_surface, draw_cities, draw_paths, draw_text
from execution import (
    ExecutionConfig,
    ExperimentRunner,
    ProcessingState,
    ProblemType,
    AlgorithmMode,
    ExperimentRequest,
)
from scenarios import list_scenarios, load_scenario
from ui.hospital_renderer import draw_hospital_solution
from execution.exporter import export_hospital_json, append_experiment_csv

WIDTH, HEIGHT = 1500, 980
GENERATIONS_PER_FRAME = 10

# Gráfico de evolução: centralizado na coluna esquerda e abaixo dos botões de rota.
PLOT_SIZE = (285, 230)
PLOT_POSITION = (62, 665)

# Linha com os pesos da função objetivo hospitalar.
WEIGHTS_POSITION = (15, 910)
WEIGHTS_MAX_WIDTH = WIDTH - 30
WEIGHTS_FONT_SIZE = 13

ALGORITHMS = ["Algoritmo Genético", "Vizinho Mais Próximo", "Comparar ambos"]
PROBLEM_TYPES = ["TSP / ATT48", "Hospitalar / VRP"]
ROUTE_GENETIC = "genetic"
ROUTE_NEAREST = "nearest"
ROUTE_HEURISTIC = "heuristic"

PARAMETER_SCOPE_AG = ("AG",)
PARAMETER_SCOPE_H = ("H",)
PARAMETER_SCOPE_BOTH = ("AG", "H")

# Nome interno, valor inicial e algoritmos aos quais o parâmetro se aplica.
# A estrutura aceita parâmetros [AG], [H] e [AG][H].
PARAMETER_FIELDS = (
    ("População", "100", PARAMETER_SCOPE_AG),
    ("Gerações", "500", PARAMETER_SCOPE_AG),
    ("Execuções", "3", PARAMETER_SCOPE_AG),
    ("Mutação", "0.10", PARAMETER_SCOPE_AG),
    ("Elitismo", "1", PARAMETER_SCOPE_AG),
    ("Semente", "", PARAMETER_SCOPE_AG),
)


def _parameter_label(name: str, scopes: tuple[str, ...]) -> str:
    # Monta o rótulo visual, por exemplo [AG] ou [AG][H].
    prefix = "".join(f"[{scope}]" for scope in scopes)
    return f"{prefix} {name}".strip()


def _active_parameter_scopes(algorithm: str) -> frozenset[str]:
    # Informa quais grupos de parâmetros estão ativos na seleção atual.
    if algorithm == ALGORITHMS[0]:
        return frozenset(PARAMETER_SCOPE_AG)
    if algorithm == ALGORITHMS[1]:
        return frozenset(PARAMETER_SCOPE_H)
    return frozenset(PARAMETER_SCOPE_BOTH)


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
    min_x = min(x for x, _ in cities)
    max_x = max(x for x, _ in cities)
    min_y = min(y for _, y in cities)
    max_y = max(y for _, y in cities)
    return [
        (
            left + (x - min_x) / (max_x - min_x) * width,
            top + (y - min_y) / (max_y - min_y) * height,
        )
        for x, y in cities
    ]


def _history_from_run(run) -> list[float]:
    """Extrai o histórico de uma execução TSP ou hospitalar.

    No TSP, o histórico fica em ``fitness_history``.
    No problema hospitalar, ``history`` contém métricas por geração e o valor
    utilizado no gráfico é ``objective_cost``.
    """
    if run is None:
        return []

    fitness_history = getattr(run, "fitness_history", None)
    if fitness_history is not None:
        return [float(value) for value in fitness_history]

    values = []
    for metric in getattr(run, "history", ()):
        objective_cost = getattr(metric, "objective_cost", None)
        if objective_cost is not None:
            values.append(float(objective_cost))
        elif isinstance(metric, (int, float)):
            values.append(float(metric))

    return values


def _format_weight(value: float) -> str:
    """Formata pesos no padrão brasileiro."""
    number = float(value)

    if number.is_integer():
        return f"{int(number):,}".replace(",", ".")

    formatted = f"{number:,.10f}".rstrip("0").rstrip(".")
    return (
        formatted
        .replace(",", "__MILHAR__")
        .replace(".", ",")
        .replace("__MILHAR__", ".")
    )


def _hospital_weights_text(weights) -> str:
    """Monta todos os pesos hospitalares em uma única linha."""
    items = (
        ("Distância", weights.distance_weight),
        ("Chegada conforme prioridade", weights.priority_arrival_weight),
        ("Atraso-base", weights.delay_weight),
        ("Excesso de capacidade", weights.capacity_excess_weight),
        ("Excesso de autonomia", weights.autonomy_excess_weight),
        ("Entrega não atendida", weights.unassigned_delivery_weight),
        ("Desequilíbrio das rotas", weights.route_balance_weight),
    )

    return "Pesos: " + ", ".join(
        f"{label}: {_format_weight(value)}"
        for label, value in items
    )


class Application:
    """Mantém separadas a vida da janela e a vida do processamento."""

    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Comparador de algoritmos TSP — ATT48")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.manager = pygame_gui.UIManager((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 17)
        self.weights_font = pygame.font.SysFont(
            "Arial",
            WEIGHTS_FONT_SIZE,
        )

        self.cities = list(att_48_cities_locations)
        self.display_cities = _scaled_cities(self.cities)

        self.runner = ExperimentRunner()

        # O Surface permanece em memória após o término. A assinatura impede
        # que o mesmo gráfico seja recriado em todos os frames da tela concluída.
        self.plot = None
        self.plot_generation = -1
        self.plot_signature = None

        self.scenario_paths = list_scenarios()
        self.current_scenario = (
            load_scenario(self.scenario_paths[0]) if self.scenario_paths else None
        )

        self.selected_route = ROUTE_GENETIC

        self.started_at = None
        self.ended_at = None
        self.paused_at = None
        self.paused_seconds = 0.0

        self._build_controls()

    def _label(self, text, y):
        pygame_gui.elements.UILabel(
            pygame.Rect(15, y, 145, 30),
            text,
            self.manager,
        )

    def _entry(self, value, y):
        entry = pygame_gui.elements.UITextEntryLine(
            pygame.Rect(165, y, 225, 30),
            self.manager,
        )
        entry.set_text(value)
        return entry

    def _build_controls(self):
        self._label(_parameter_label("Tipo", PARAMETER_SCOPE_BOTH), 435)
        self.problem_type = pygame_gui.elements.UIDropDownMenu(
            PROBLEM_TYPES,
            PROBLEM_TYPES[0],
            pygame.Rect(165, 435, 225, 35),
            self.manager,
        )

        scenario_names = [p.stem for p in self.scenario_paths] or ["Nenhum cenário"]

        self._label(_parameter_label("Cenário", PARAMETER_SCOPE_BOTH), 477)
        self.scenario_dropdown = pygame_gui.elements.UIDropDownMenu(
            scenario_names,
            scenario_names[0],
            pygame.Rect(165, 477, 225, 35),
            self.manager,
        )

        self._label("Exibir veículo", 519)
        vehicle_names = (
            ["Todas as rotas"] + [v.name for v in self.current_scenario.vehicles]
            if self.current_scenario
            else ["Todas as rotas"]
        )
        self.vehicle_dropdown = pygame_gui.elements.UIDropDownMenu(
            vehicle_names,
            vehicle_names[0],
            pygame.Rect(165, 519, 225, 35),
            self.manager,
        )

        self._label("Algoritmo", 20)
        self.algorithm = pygame_gui.elements.UIDropDownMenu(
            ALGORITHMS,
            ALGORITHMS[0],
            pygame.Rect(165, 20, 225, 35),
            self.manager,
        )

        self.entries = {}
        self.parameter_scopes = {}

        for i, (name, value, scopes) in enumerate(PARAMETER_FIELDS):
            y = 70 + i * 42
            self._label(_parameter_label(name, scopes), y)
            self.entries[name] = self._entry(value, y)
            self.parameter_scopes[name] = frozenset(scopes)

        self.parameter_legend = pygame_gui.elements.UILabel(
            pygame.Rect(15, 310, 375, 25),
            "[AG] Genético    [H] Heurístico",
            self.manager,
        )
        self._update_parameter_states()

        labels = [
            ("Processar", 15, 340),
            ("Pausar", 145, 340),
            ("Continuar", 275, 340),
            ("Cancelar", 15, 385),
            ("Limpar resultados", 210, 385),
        ]
        self.buttons = {
            name: pygame_gui.elements.UIButton(
                pygame.Rect(
                    x,
                    y,
                    120 if name != "Limpar resultados" else 180,
                    35,
                ),
                name,
                self.manager,
            )
            for name, x, y in labels
        }

        self.buttons["Exportar resultado"] = pygame_gui.elements.UIButton(
            pygame.Rect(15, 570, 180, 35),
            "Exportar resultado",
            self.manager,
        )

        self.route_buttons = {
            ROUTE_GENETIC: pygame_gui.elements.UIButton(
                pygame.Rect(15, 615, 180, 35),
                "Rota Genética",
                self.manager,
            ),
            ROUTE_NEAREST: pygame_gui.elements.UIButton(
                pygame.Rect(210, 615, 180, 35),
                "Rota Vizinho",
                self.manager,
            ),
        }
        self._update_route_buttons()

        # Indicador somente de leitura: o algoritmo ativo é controlado pelo
        # runner, portanto não deve parecer uma opção que o usuário precisa
        # alterar durante o processamento.
        self.processing_algorithm_label = pygame_gui.elements.UILabel(
            pygame.Rect(1180, 20, 285, 35),
            "Algoritmo: aguardando processamento",
            self.manager,
        )

    def _update_parameter_states(self):
        # Habilita somente os campos aplicáveis ao algoritmo selecionado.
        active_scopes = _active_parameter_scopes(_dropdown_value(self.algorithm))

        for name, entry in self.entries.items():
            if self.parameter_scopes[name] & active_scopes:
                entry.enable()
            else:
                entry.disable()

    def _config(self):
        algorithm = _dropdown_value(self.algorithm)

        # A heurística atual é determinística e não consome os parâmetros do AG.
        # Usar os valores padrão impede que um texto inválido em campo [AG]
        # bloqueie uma execução exclusivamente heurística.
        if algorithm == ALGORITHMS[1]:
            return ExecutionConfig(algorithm=algorithm)

        def integer(name):
            return int(self.entries[name].get_text())

        seed = self.entries["Semente"].get_text().strip()

        return ExecutionConfig(
            algorithm=algorithm,
            population_size=integer("População"),
            generations=integer("Gerações"),
            executions=integer("Execuções"),
            mutation_probability=float(
                self.entries["Mutação"].get_text().replace(",", ".")
            ),
            elite_count=integer("Elitismo"),
            random_seed=int(seed) if seed else None,
        )

    def _request(self):
        config = self._config()
        algorithm = _dropdown_value(self.algorithm)

        mode = (
            AlgorithmMode.COMPARE
            if algorithm == "Comparar ambos"
            else (
                AlgorithmMode.HEURISTIC
                if algorithm.startswith("Vizinho")
                else AlgorithmMode.GENETIC
            )
        )

        if _dropdown_value(self.problem_type) == PROBLEM_TYPES[0]:
            return ExperimentRequest(
                ProblemType.TSP,
                mode,
                config,
                tuple(self.cities),
            )

        selected = _dropdown_value(self.scenario_dropdown)
        path = next(p for p in self.scenario_paths if p.stem == selected)
        self.current_scenario = load_scenario(path)

        return ExperimentRequest(
            ProblemType.HOSPITAL,
            mode,
            config,
            hospital_scenario=self.current_scenario,
        )

    def _reset_plot(self):
        """Remove o gráfico somente para uma nova execução ou limpeza manual."""
        self.plot = None
        self.plot_generation = -1
        self.plot_signature = None

    def _click(self, button):
        try:
            # Trata primeiro os seletores de rota. A comparação por identidade
            # evita que o pygame_gui confunda elementos com atributos semelhantes.
            if button is self.route_buttons[ROUTE_GENETIC]:
                self._select_route(ROUTE_GENETIC)

            elif button is self.route_buttons[ROUTE_NEAREST]:
                self._select_route(ROUTE_NEAREST)

            elif button == self.buttons["Processar"]:
                self.runner.start(self._request())
                self.started_at = time.perf_counter()
                self.ended_at = None
                self.paused_at = None
                self.paused_seconds = 0.0
                self._reset_plot()
                self.selected_route = ROUTE_GENETIC
                self._update_route_buttons()

            elif button == self.buttons["Pausar"]:
                was_running = self.runner.state is ProcessingState.RUNNING
                self.runner.pause()

                if was_running and self.runner.state is ProcessingState.PAUSED:
                    self.paused_at = time.perf_counter()

                self._refresh_plot(True)

            elif button == self.buttons["Continuar"]:
                was_paused = self.runner.state is ProcessingState.PAUSED
                self.runner.resume()

                if (
                    was_paused
                    and self.runner.state is ProcessingState.RUNNING
                    and self.paused_at is not None
                ):
                    self.paused_seconds += time.perf_counter() - self.paused_at
                    self.paused_at = None

            elif button == self.buttons["Cancelar"]:
                self.runner.cancel()
                self._stop_timer()
                self._refresh_plot(True)

            elif button == self.buttons["Limpar resultados"]:
                self.runner.clear()
                self._reset_plot()
                self.started_at = None
                self.ended_at = None
                self.paused_at = None
                self.paused_seconds = 0.0
                self.selected_route = ROUTE_GENETIC
                self._update_route_buttons()

            elif button == self.buttons["Exportar resultado"]:
                self._export_result()

        except (ValueError, TypeError) as error:
            self.runner.fail(error)

    def _select_route(self, route_name):
        """Seleciona uma das duas rotas consolidadas da comparação."""
        if self.runner.get_comparison() and route_name in (
            ROUTE_GENETIC,
            ROUTE_NEAREST,
        ):
            is_hospital = (
                self.runner.get_snapshot().problem_type is ProblemType.HOSPITAL
            )
            self.selected_route = (
                ROUTE_HEURISTIC
                if route_name == ROUTE_NEAREST and is_hospital
                else route_name
            )
            self._update_route_buttons()

    def _update_route_buttons(self):
        selected = self.selected_route
        hospital = (
            self.runner.get_snapshot().problem_type is ProblemType.HOSPITAL
        )

        self.route_buttons[ROUTE_GENETIC].set_text(
            "✓ Rota Genética" if selected == ROUTE_GENETIC else "Rota Genética"
        )

        heuristic_selected = selected in (ROUTE_NEAREST, ROUTE_HEURISTIC)
        label = "Rota Heurística" if hospital else "Rota Vizinho"

        self.route_buttons[ROUTE_NEAREST].set_text(
            ("✓ " if heuristic_selected else "") + label
        )

    def _get_displayed_hospital_solution(self):
        return self.runner.get_display_solution(self.selected_route)

    def _selected_vehicle_id(self):
        if not self.current_scenario:
            return None

        selected = _dropdown_value(self.vehicle_dropdown)
        vehicle = next(
            (
                v
                for v in self.current_scenario.vehicles
                if v.name == selected
            ),
            None,
        )
        return vehicle.id if vehicle else None

    def _export_result(self):
        if not self.runner.can_export():
            self.runner.message = "Não há resultado hospitalar para exportar."
            return

        try:
            comparison = self.runner.get_comparison()

            if self.runner.partial_result:
                runs = [("partial", self.runner.partial_result)]
            elif comparison:
                runs = [
                    ("genetic", comparison.genetic.best_run),
                    ("heuristic", comparison.heuristic.best_run),
                ]
            else:
                runs = [
                    (
                        self.runner.get_snapshot().algorithm_mode.value,
                        self.runner.get_result().best_run,
                    )
                ]

            paths = []
            for algorithm, run in runs:
                paths.append(
                    str(
                        export_hospital_json(
                            self.current_scenario,
                            algorithm,
                            self.runner.config,
                            run,
                        )
                    )
                )
                append_experiment_csv(
                    self.current_scenario,
                    algorithm,
                    self.runner.config,
                    run,
                )

            self.runner.message = (
                "Resultado exportado com sucesso: " + ", ".join(paths)
            )

        except Exception as error:
            self.runner.message = f"Falha ao exportar: {error}"

    def _build_tsp_result_lines(self, result):
        return [
            f"Melhor distância: {result.best_run.best_fitness:,.2f}",
            f"Distância média: {result.average_fitness:,.2f}",
            f"Pior distância: {result.worst_fitness:,.2f}",
            f"Desvio-padrão: {result.standard_deviation:,.2f}",
            f"Tempo médio: {result.average_elapsed_seconds:.2f} s",
            f"Melhor execução: {result.best_run.execution_number}",
        ]

    def _build_hospital_result_lines(self, result):
        run = result.best_run
        solution = run.solution
        delivered = sum(len(route.stops) for route in solution.routes)
        used = sum(bool(route.stops) for route in solution.routes)

        return [
            f"Custo objetivo: {solution.objective_cost:,.2f}",
            f"Distância total: {solution.total_distance_km:,.2f} km",
            f"Duração total: {solution.total_duration_minutes:,.2f} min",
            f"Atraso total: {solution.total_delay_minutes:,.2f} min",
            f"Entregas atendidas: {delivered}",
            f"Não atendidas: {len(solution.unassigned_deliveries)}",
            f"Veículos utilizados: {used}",
            f"Média do custo: {result.average_objective_cost:,.2f}",
            f"Pior custo: {result.worst_objective_cost:,.2f}",
            f"Desvio-padrão: {result.standard_deviation:,.2f}",
            f"Tempo médio: {result.average_elapsed_seconds:.2f} s",
            f"Melhor execução: {run.execution_number}",
        ]

    def _build_tsp_comparison_lines(self, comparison):
        return [
            "COMPARAÇÃO",
            f"Genético: {comparison.genetic.best_run.best_fitness:,.2f}",
            f"Vizinho: {comparison.nearest.best_run.best_fitness:,.2f}",
            f"Diferença: {comparison.absolute_difference:,.2f}",
            f"Melhoria do AG: {comparison.improvement_percentage:.2f}%",
        ]

    def _build_hospital_comparison_lines(self, comparison):
        genetic = comparison.genetic.best_run.solution
        heuristic = comparison.heuristic.best_run.solution

        return [
            "COMPARAÇÃO HOSPITALAR",
            f"AG custo: {genetic.objective_cost:,.2f}",
            f"AG distância: {genetic.total_distance_km:,.2f}",
            f"AG atraso: {genetic.total_delay_minutes:,.2f}",
            f"Heurística custo: {heuristic.objective_cost:,.2f}",
            f"Heurística distância: {heuristic.total_distance_km:,.2f}",
            f"Heurística atraso: {heuristic.total_delay_minutes:,.2f}",
            f"Diferença custo: {comparison.objective_difference:,.2f}",
            f"Melhoria AG: {comparison.improvement_percentage:.2f}%",
            f"Diferença distância: {comparison.distance_difference_km:,.2f}",
            f"Diferença atraso: {comparison.delay_difference_minutes:,.2f}",
            f"Diferença não atendidas: {comparison.unassigned_difference}",
        ]

    def _get_plot_history(self):
        """Seleciona o histórico que deve permanecer desenhado.

        Durante ``Comparar ambos``, o runner troca o optimizer do AG pelo
        optimizer heurístico. O histórico da heurística contém apenas um ponto.
        Nesse intervalo, devolvemos ``None`` para manter o Surface já desenhado.

        Após a comparação ser consolidada, recuperamos o histórico da melhor
        execução genética armazenada no resultado final.
        """
        comparison = self.runner.get_comparison()

        if comparison is not None:
            return (
                _history_from_run(comparison.genetic.best_run),
                "comparison-final-genetic",
            )

        snapshot = self.runner.get_snapshot()

        if (
            snapshot.algorithm_mode is AlgorithmMode.COMPARE
            and snapshot.current_phase in ("heuristic", "nearest")
        ):
            # Não substitui o gráfico do AG pelo gráfico de um único ponto
            # produzido pela heurística.
            return None, None

        result = self.runner.get_result()

        if (
            result is not None
            and self.runner.state is ProcessingState.FINISHED
            and snapshot.algorithm_mode is AlgorithmMode.GENETIC
        ):
            return (
                _history_from_run(result.best_run),
                "genetic-final",
            )

        return (
            list(self.runner.history),
            f"live-{snapshot.current_phase or 'idle'}",
        )

    def _refresh_plot(self, force=False):
        history, source = self._get_plot_history()

        # ``None`` significa: mantenha o Surface que já está em self.plot.
        if history is None:
            return

        if not history:
            return

        signature = (
            source,
            len(history),
            history[-1],
        )
        history_changed = signature != self.plot_signature
        periodic_refresh = len(history) - self.plot_generation >= 10

        if (
            history_changed
            and (
                force
                or periodic_refresh
                or self.plot is None
            )
        ):
            self.plot = create_plot_surface(
                range(1, len(history) + 1),
                history,
                PLOT_SIZE,
            )
            self.plot_generation = len(history)
            self.plot_signature = signature

    def _stop_timer(self):
        """Congela o cronômetro na primeira conclusão ou cancelamento."""
        if self.started_at is not None and self.ended_at is None:
            self.ended_at = time.perf_counter()

    def _elapsed_time(self):
        """Retorna apenas o tempo efetivo de processamento, excluindo pausas."""
        if self.started_at is None:
            return 0.0

        end = (
            self.ended_at
            if self.ended_at is not None
            else time.perf_counter()
        )
        paused = self.paused_seconds

        if self.paused_at is not None:
            paused += end - self.paused_at

        return max(0.0, end - self.started_at - paused)

    def _route(self):
        route = self.runner.best_route

        if self.runner.comparison:
            result = (
                self.runner.comparison.nearest
                if self.selected_route == ROUTE_NEAREST
                else self.runner.comparison.genetic
            )
            route = result.best_run.best_route

        index = {
            city: i
            for i, city in enumerate(self.cities)
        }
        return [
            self.display_cities[index[city]]
            for city in route
        ]

    def _update_algorithm_label(self):
        """Atualiza o texto da direita conforme a fase realmente executada."""
        if self.runner.state == ProcessingState.IDLE:
            text = "Algoritmo: aguardando processamento"

        elif self.runner.state == ProcessingState.ERROR:
            text = "Algoritmo: não iniciado"

        elif self.runner.comparison:
            if self.selected_route in (ROUTE_NEAREST, ROUTE_HEURISTIC):
                name = (
                    "Heurística Hospitalar"
                    if self.selected_route == ROUTE_HEURISTIC
                    else "Vizinho Mais Próximo"
                )
            else:
                name = "Algoritmo Genético"

            text = f"Rota exibida: {name}"

        elif self.runner.get_snapshot().current_phase in (
            "nearest",
            "heuristic",
        ):
            text = "Processando: Vizinho Mais Próximo"

        else:
            text = "Processando: Algoritmo Genético"

        self.processing_algorithm_label.set_text(text)

    def _lines(self):
        state_names = {
            "idle": "Aguardando",
            "running": "Processando",
            "paused": "Pausado",
            "finished": "Concluído",
            "cancelled": "Cancelado",
            "error": "Erro",
        }

        lines = [
            f"Status: {state_names[self.runner.state.value]}"
        ]
        snapshot = self.runner.get_snapshot()

        if self.runner.config:
            lines += [
                (
                    f"Execução: {snapshot.current_execution} "
                    f"de {snapshot.total_executions}"
                ),
                (
                    f"Geração: {snapshot.current_generation} "
                    f"de {snapshot.total_generations}"
                ),
            ]

        if self.runner.best_fitness != float("inf"):
            lines.append(
                f"Melhor atual: {self.runner.best_fitness:,.2f}"
            )

        if self.started_at:
            lines.append(
                f"Tempo decorrido: {self._elapsed_time():.2f} s"
            )

        result = self.runner.get_result()
        comparison = self.runner.get_comparison()

        if result:
            lines += [""] + (
                self._build_hospital_result_lines(result)
                if snapshot.problem_type is ProblemType.HOSPITAL
                else self._build_tsp_result_lines(result)
            )

        if comparison:
            lines += [""] + (
                self._build_hospital_comparison_lines(comparison)
                if snapshot.problem_type is ProblemType.HOSPITAL
                else self._build_tsp_comparison_lines(comparison)
            )

        if comparison and comparison.improvement_percentage < 0:
            lines.append("O AG encontrou uma solução pior.")

        if self.runner.message:
            lines += ["", self.runner.message]

        return lines

    def _draw_hospital_weights(self, snapshot):
        """Desenha os pesos hospitalares abaixo do gráfico, em uma linha."""
        if (
            snapshot.problem_type is not ProblemType.HOSPITAL
            or self.current_scenario is None
        ):
            return

        weights = self.current_scenario.fitness_weights
        text = _hospital_weights_text(weights)

        text_surface = self.weights_font.render(
            text,
            True,
            (25, 30, 40),
        )

        # Mantém todo o conteúdo em uma única linha.
        if text_surface.get_width() > WEIGHTS_MAX_WIDTH:
            scale = WEIGHTS_MAX_WIDTH / text_surface.get_width()
            resized_height = max(
                10,
                round(text_surface.get_height() * scale),
            )
            text_surface = pygame.transform.smoothscale(
                text_surface,
                (WEIGHTS_MAX_WIDTH, resized_height),
            )

        pygame.draw.line(
            self.screen,
            (203, 213, 225),
            (15, WEIGHTS_POSITION[1] - 7),
            (WIDTH - 15, WEIGHTS_POSITION[1] - 7),
            1,
        )

        pygame.draw.rect(
            self.screen,
            (245, 247, 250),
            pygame.Rect(
                10,
                WEIGHTS_POSITION[1] - 4,
                WIDTH - 20,
                text_surface.get_height() + 8,
            ),
            border_radius=4,
        )

        self.screen.blit(
            text_surface,
            WEIGHTS_POSITION,
        )

    def draw(self):
        self._update_algorithm_label()
        snapshot = self.runner.get_snapshot()

        self.screen.fill((245, 247, 250))
        pygame.draw.rect(
            self.screen,
            (255, 255, 255),
            (410, 20, 770, 810),
        )
        pygame.draw.rect(
            self.screen,
            (255, 255, 255),
            (1170, 70, 315, 760),
        )

        hospital_solution = (
            self._get_displayed_hospital_solution()
            if snapshot.problem_type is ProblemType.HOSPITAL
            else None
        )
        route = [] if hospital_solution else self._route()

        if hospital_solution:
            draw_hospital_solution(
                self.screen,
                self.current_scenario,
                hospital_solution,
                pygame.Rect(410, 20, 770, 810),
                self.font,
                vehicle_id=self._selected_vehicle_id(),
            )

        elif route:
            route_color = (
                (234, 88, 12)
                if (
                    self.selected_route == ROUTE_NEAREST
                    and self.runner.comparison
                )
                else (37, 99, 235)
            )
            draw_paths(
                self.screen,
                route,
                route_color,
                3,
            )

        if snapshot.problem_type is not ProblemType.HOSPITAL:
            draw_cities(
                self.screen,
                self.display_cities,
                (220, 38, 38),
                5,
            )

        if self.plot:
            self.screen.blit(
                self.plot,
                PLOT_POSITION,
            )

        self._draw_hospital_weights(snapshot)

        for i, line in enumerate(self._lines()):
            draw_text(
                self.screen,
                line,
                (25, 30, 40),
                (1190, 85 + i * 25),
                self.font,
            )

        self.manager.draw_ui(self.screen)
        pygame.display.flip()

    def run(self):
        application_running = True

        while application_running:
            delta = self.clock.tick(60) / 1000

            for event in pygame.event.get():
                if (
                    event.type == pygame.QUIT
                    or (
                        event.type == pygame.KEYDOWN
                        and event.key in (pygame.K_q, pygame.K_ESCAPE)
                    )
                ):
                    application_running = False

                is_button_event = (
                    event.type == pygame_gui.UI_BUTTON_PRESSED
                    or getattr(event, "user_type", None)
                    == pygame_gui.UI_BUTTON_PRESSED
                )
                if is_button_event:
                    self._click(event.ui_element)

                is_dropdown_event = (
                    event.type == pygame_gui.UI_DROP_DOWN_MENU_CHANGED
                    or getattr(event, "user_type", None)
                    == pygame_gui.UI_DROP_DOWN_MENU_CHANGED
                )

                self.manager.process_events(event)

                if (
                    is_dropdown_event
                    and event.ui_element is self.algorithm
                ):
                    self._update_parameter_states()

            self.runner.step(GENERATIONS_PER_FRAME)

            if self.runner.state in (
                ProcessingState.FINISHED,
                ProcessingState.CANCELLED,
                ProcessingState.ERROR,
            ):
                self._stop_timer()

            self._refresh_plot(
                self.runner.state in (
                    ProcessingState.FINISHED,
                    ProcessingState.CANCELLED,
                )
            )

            self.manager.update(delta)
            self.draw()

        pygame.quit()


def run_application():
    """Inicia a aplicação; ponto público compartilhado por app.py e tsp.py."""
    Application().run()
