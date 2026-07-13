from .loader import list_scenarios, load_scenario, ScenarioRepository
from .csv_importer import import_deliveries_csv, import_vehicles_csv
__all__=["list_scenarios","load_scenario","ScenarioRepository","import_deliveries_csv","import_vehicles_csv"]


# Autonomia insuficiente: 14 entregas, com destinos urbanos, rotas longas e duas bases realmente fora do alcance.
# Capacidade insuficiente: mistura falta de capacidade acumulada com uma carga que excede todos os veículos.
# Entrega impossível: possui entregas normais e impossibilidades distintas por peso e autonomia.
# Frota heterogênea: 4 veículos com diferenças relevantes de velocidade, capacidade e alcance.
# Prazos apertados: 15 entregas, permitindo que a ordem escolhida gere ou evite atrasos.
# Prioridades: entregas regulares próximas competem com entregas críticas mais distantes.
# Viável: cenário balanceado com 20 entregas e 4 veículos, sem impossibilidades estruturais.