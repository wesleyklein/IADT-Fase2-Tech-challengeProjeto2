from ui.application import (
    PARAMETER_SCOPE_AG,
    PARAMETER_SCOPE_BOTH,
    PARAMETER_SCOPE_H,
    _active_parameter_scopes,
    _dropdown_value,
    _parameter_label,
)


class Dropdown:
    def __init__(self, selected_option):
        self.selected_option = selected_option


def test_dropdown_value_accepts_string_and_pygame_gui_tuple():
    assert _dropdown_value(Dropdown("Algoritmo Genético")) == "Algoritmo Genético"
    assert _dropdown_value(Dropdown(("Vizinho Mais Próximo", "Vizinho Mais Próximo"))) == "Vizinho Mais Próximo"



def test_parameter_label_supports_one_or_two_algorithm_prefixes():
    assert _parameter_label("População", PARAMETER_SCOPE_AG) == "[AG] População"
    assert _parameter_label("Tentativas", PARAMETER_SCOPE_H) == "[H] Tentativas"
    assert _parameter_label("Tipo", PARAMETER_SCOPE_BOTH) == "[AG][H] Tipo"


def test_active_parameter_scopes_follow_algorithm_selection():
    assert _active_parameter_scopes("Algoritmo Genético") == frozenset({"AG"})
    assert _active_parameter_scopes("Vizinho Mais Próximo") == frozenset({"H"})
    assert _active_parameter_scopes("Comparar ambos") == frozenset({"AG", "H"})
