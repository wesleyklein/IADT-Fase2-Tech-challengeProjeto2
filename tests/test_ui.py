from ui.application import _dropdown_value


class Dropdown:
    def __init__(self, selected_option):
        self.selected_option = selected_option


def test_dropdown_value_accepts_string_and_pygame_gui_tuple():
    assert _dropdown_value(Dropdown("Algoritmo Genético")) == "Algoritmo Genético"
    assert _dropdown_value(Dropdown(("Vizinho Mais Próximo", "Vizinho Mais Próximo"))) == "Vizinho Mais Próximo"
