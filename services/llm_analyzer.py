"""Integração mínima com a OpenAI para interpretar resultados do TSP/VRP."""
from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

from execution import ProblemType


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_ROOT / ".env"
DEFAULT_MODEL = "gpt-4.1-mini"
DEFAULT_MAX_OUTPUT_TOKENS = 1800

SYSTEM_INSTRUCTIONS = """
Você é um especialista em pesquisa operacional, algoritmos genéticos, TSP e
roteamento de veículos hospitalares.

Analise exclusivamente os dados JSON recebidos. Não invente valores, rotas,
restrições ou resultados. O campo custo objetivo é uma pontuação da função de
fitness e não representa dinheiro.

Responda em português do Brasil, de forma objetiva e didática, usando:
1. Resumo executivo.
2. Explicação dos fatores que mais influenciaram o resultado.
3. Comparação entre algoritmos, quando houver.
4. Recomendações práticas para os próximos testes.

Use no máximo 700 palavras. Ao recomendar parâmetros, deixe claro que são
sugestões experimentais e que devem ser validadas em várias sementes e execuções.
""".strip()


class LlmConfigurationError(RuntimeError):
    """Erro de configuração local da integração."""


class LlmAnalysisError(RuntimeError):
    """Erro ao solicitar ou interpretar a resposta da API."""


def _rounded(value: Any, digits: int = 4):
    if isinstance(value, float):
        return round(value, digits)
    return value


def _execution_config_payload(config) -> dict[str, Any]:
    if config is None:
        return {}
    return {
        "algorithm": config.algorithm,
        "population_size": config.population_size,
        "generations": config.generations,
        "executions": config.executions,
        "mutation_probability": config.mutation_probability,
        "elite_count": config.elite_count,
        "random_seed": config.random_seed,
    }


def _tsp_route_indices(route, cities) -> list[int | str]:
    city_index = {tuple(city): index for index, city in enumerate(cities, start=1)}
    result: list[int | str] = []
    for city in route:
        key = tuple(city)
        result.append(city_index.get(key, str(key)))
    return result


def _tsp_result_payload(result, cities) -> dict[str, Any]:
    best = result.best_run
    return {
        "algorithm": result.algorithm,
        "runs": len(result.runs),
        "best_distance": _rounded(best.best_fitness),
        "average_distance": _rounded(result.average_fitness),
        "worst_distance": _rounded(result.worst_fitness),
        "standard_deviation": _rounded(result.standard_deviation),
        "average_elapsed_seconds": _rounded(result.average_elapsed_seconds),
        "best_execution": best.execution_number,
        "best_seed": best.seed,
        "best_route_city_order": _tsp_route_indices(best.best_route, cities),
    }


def _stop_payload(stop) -> dict[str, Any]:
    return {
        "sequence": stop.sequence,
        "delivery_id": stop.delivery.id,
        "delivery_name": stop.delivery.name,
        "priority": stop.delivery.priority.name,
        "arrival_minutes": _rounded(stop.arrival_time_minutes),
        "deadline_minutes": _rounded(stop.delivery.deadline_minutes),
        "delay_minutes": _rounded(stop.delay_minutes),
        "cumulative_distance_km": _rounded(stop.cumulative_distance_km),
        "cumulative_load_kg": _rounded(stop.cumulative_load_kg),
    }


def _route_payload(route) -> dict[str, Any]:
    return {
        "vehicle_id": route.vehicle.id,
        "vehicle_name": route.vehicle.name,
        "vehicle_capacity_kg": _rounded(route.vehicle.capacity_kg),
        "vehicle_autonomy_km": _rounded(route.vehicle.autonomy_km),
        "vehicle_average_speed_kmh": _rounded(route.vehicle.average_speed_kmh),
        "total_distance_km": _rounded(route.total_distance_km),
        "total_load_kg": _rounded(route.total_load_kg),
        "total_duration_minutes": _rounded(route.total_duration_minutes),
        "capacity_excess_kg": _rounded(route.capacity_excess_kg),
        "autonomy_excess_km": _rounded(route.autonomy_excess_km),
        "stops": [_stop_payload(stop) for stop in route.stops],
    }


def _solution_payload(solution) -> dict[str, Any]:
    delivered = sum(len(route.stops) for route in solution.routes)
    used = sum(bool(route.stops) for route in solution.routes)

    return {
        "is_feasible": solution.is_feasible,
        "objective_cost": _rounded(solution.objective_cost),
        "total_distance_km": _rounded(solution.total_distance_km),
        "total_duration_minutes": _rounded(solution.total_duration_minutes),
        "total_delay_minutes": _rounded(solution.total_delay_minutes),
        "delivered_count": delivered,
        "unassigned_count": len(solution.unassigned_deliveries),
        "vehicles_used": used,
        "penalties": {
            "priority_cost": _rounded(solution.total_priority_cost),
            "delay_penalty": _rounded(solution.total_delay_penalty),
            "capacity_penalty": _rounded(solution.total_capacity_penalty),
            "autonomy_penalty": _rounded(solution.total_autonomy_penalty),
            "unassigned_penalty": _rounded(solution.total_unassigned_penalty),
            "balance_penalty": _rounded(solution.total_balance_penalty),
        },
        "unassigned_deliveries": [
            {
                "delivery_id": item.delivery.id,
                "delivery_name": item.delivery.name,
                "priority": item.delivery.priority.name,
                "reason": item.reason.value,
                "details": item.details,
            }
            for item in solution.unassigned_deliveries
        ],
        "routes": [_route_payload(route) for route in solution.routes],
    }


def _hospital_run_payload(run) -> dict[str, Any]:
    return {
        "execution_number": run.execution_number,
        "seed": run.seed,
        "elapsed_seconds": _rounded(run.elapsed_seconds),
        "is_partial": run.is_partial,
        "solution": _solution_payload(run.solution),
    }


def _hospital_result_payload(result) -> dict[str, Any]:
    return {
        "algorithm": result.algorithm,
        "runs": len(result.runs),
        "average_objective_cost": _rounded(result.average_objective_cost),
        "worst_objective_cost": _rounded(result.worst_objective_cost),
        "standard_deviation": _rounded(result.standard_deviation),
        "average_elapsed_seconds": _rounded(result.average_elapsed_seconds),
        "best_run": _hospital_run_payload(result.best_run),
    }


def _fitness_weights_payload(scenario) -> dict[str, Any]:
    weights = getattr(scenario, "fitness_weights", None)
    if weights is None:
        return {}
    if is_dataclass(weights):
        return {key: _rounded(value) for key, value in asdict(weights).items()}
    return {}


def build_analysis_payload(runner, current_scenario=None) -> dict[str, Any]:
    """Converte somente o resultado consolidado em um JSON compacto para a LLM."""
    snapshot = runner.get_snapshot()
    result = runner.get_result()
    comparison = runner.get_comparison()
    partial = runner.partial_result

    if snapshot.problem_type is None:
        raise ValueError("Execute um processamento antes de solicitar a análise com IA.")

    if not any((result, comparison, partial)):
        raise ValueError(
            "Ainda não há resultado consolidado para analisar. "
            "Aguarde a conclusão ou cancele uma execução hospitalar para gerar um parcial."
        )

    payload: dict[str, Any] = {
        "problem_type": snapshot.problem_type.value,
        "algorithm_mode": snapshot.algorithm_mode.value if snapshot.algorithm_mode else None,
        "execution_parameters": _execution_config_payload(runner.config),
        "processing_elapsed_seconds": _rounded(snapshot.elapsed_seconds),
        "status": snapshot.state.value,
    }

    if snapshot.problem_type is ProblemType.TSP:
        cities = runner.request.tsp_cities
        payload["scenario"] = {
            "id": "att48",
            "name": "ATT48",
            "city_count": len(cities),
        }

        if comparison is not None:
            payload["results"] = {
                "genetic": _tsp_result_payload(comparison.genetic, cities),
                "nearest_neighbor": _tsp_result_payload(comparison.nearest, cities),
                "comparison": {
                    "absolute_difference": _rounded(comparison.absolute_difference),
                    "genetic_improvement_percentage": _rounded(
                        comparison.improvement_percentage
                    ),
                },
            }
        else:
            payload["results"] = {
                "single_result": _tsp_result_payload(result, cities),
            }

        return payload

    scenario = (
        runner.request.hospital_scenario
        if runner.request and runner.request.hospital_scenario is not None
        else current_scenario
    )

    payload["scenario"] = {
        "id": getattr(scenario, "id", None),
        "name": getattr(scenario, "name", None),
        "vehicle_count": len(getattr(scenario, "vehicles", ())),
        "delivery_count": len(getattr(scenario, "deliveries", ())),
        "fitness_weights": _fitness_weights_payload(scenario),
    }

    if partial is not None and result is None and comparison is None:
        payload["results"] = {"partial_result": _hospital_run_payload(partial)}
    elif comparison is not None:
        payload["results"] = {
            "genetic": _hospital_result_payload(comparison.genetic),
            "heuristic": _hospital_result_payload(comparison.heuristic),
            "comparison": {
                "objective_difference": _rounded(comparison.objective_difference),
                "genetic_improvement_percentage": _rounded(
                    comparison.improvement_percentage
                ),
                "distance_difference_km": _rounded(
                    comparison.distance_difference_km
                ),
                "delay_difference_minutes": _rounded(
                    comparison.delay_difference_minutes
                ),
                "unassigned_difference": comparison.unassigned_difference,
            },
        }
    else:
        payload["results"] = {
            "single_result": _hospital_result_payload(result),
        }

    return payload


class LlmAnalyzer:
    """Cliente simples para uma única análise após o processamento."""

    def __init__(
        self,
        client=None,
        model: str | None = None,
        max_output_tokens: int | None = None,
    ):
        load_dotenv(ENV_PATH, override=False)

        self.model = (
            model
            or os.getenv("OPENAI_MODEL", DEFAULT_MODEL).strip()
            or DEFAULT_MODEL
        )

        configured_limit = (
            max_output_tokens
            if max_output_tokens is not None
            else os.getenv("OPENAI_MAX_OUTPUT_TOKENS", str(DEFAULT_MAX_OUTPUT_TOKENS))
        )

        try:
            self.max_output_tokens = int(configured_limit)
        except (TypeError, ValueError) as error:
            raise LlmConfigurationError(
                "OPENAI_MAX_OUTPUT_TOKENS deve ser um número inteiro."
            ) from error

        if self.max_output_tokens <= 0:
            raise LlmConfigurationError(
                "OPENAI_MAX_OUTPUT_TOKENS deve ser maior que zero."
            )

        if client is not None:
            self.client = client
            return

        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise LlmConfigurationError(
                "Preencha OPENAI_API_KEY no arquivo .env localizado na raiz do projeto."
            )

        self.client = OpenAI(api_key=api_key, timeout=60.0)

    def analyze(self, payload: dict[str, Any]) -> str:
        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=SYSTEM_INSTRUCTIONS,
                input=json.dumps(payload, ensure_ascii=False, indent=2),
                max_output_tokens=self.max_output_tokens,
            )
        except AuthenticationError as error:
            raise LlmAnalysisError(
                "A chave OPENAI_API_KEY foi recusada. Confira o valor no arquivo .env."
            ) from error
        except RateLimitError as error:
            raise LlmAnalysisError(
                "A conta atingiu um limite de uso ou não possui crédito disponível."
            ) from error
        except APIConnectionError as error:
            raise LlmAnalysisError(
                "Não foi possível conectar à API da OpenAI. Verifique a internet."
            ) from error
        except APIStatusError as error:
            raise LlmAnalysisError(
                f"A API da OpenAI retornou o status HTTP {error.status_code}."
            ) from error
        except Exception as error:
            raise LlmAnalysisError(f"Falha inesperada ao consultar a OpenAI: {error}") from error

        status = getattr(response, "status", None)
        incomplete_details = getattr(response, "incomplete_details", None)
        incomplete_reason = getattr(incomplete_details, "reason", None)

        if status == "incomplete":
            if incomplete_reason == "max_output_tokens":
                raise LlmAnalysisError(
                    "A resposta atingiu o limite de saída configurado. "
                    "Aumente OPENAI_MAX_OUTPUT_TOKENS no arquivo .env."
                )
            raise LlmAnalysisError(
                f"A API retornou uma resposta incompleta. Motivo: "
                f"{incomplete_reason or 'não informado'}."
            )

        text = (response.output_text or "").strip()
        if text:
            return text

        refusal_messages = []
        output_types = []

        for item in getattr(response, "output", ()) or ():
            output_types.append(getattr(item, "type", type(item).__name__))
            for content in getattr(item, "content", ()) or ():
                content_type = getattr(content, "type", None)
                if content_type == "output_text":
                    value = (getattr(content, "text", "") or "").strip()
                    if value:
                        return value
                elif content_type == "refusal":
                    value = (getattr(content, "refusal", "") or "").strip()
                    if value:
                        refusal_messages.append(value)

        if refusal_messages:
            raise LlmAnalysisError(
                "A solicitação foi recusada pelo modelo: "
                + " ".join(refusal_messages)
            )

        raise LlmAnalysisError(
            "A API concluiu a requisição sem conteúdo textual. "
            f"Status: {status or 'não informado'}; "
            f"tipos retornados: {', '.join(output_types) or 'nenhum'}."
        )
