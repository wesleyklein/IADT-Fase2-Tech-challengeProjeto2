"""Funções de desenho reutilizáveis pela interface Pygame."""
from typing import Sequence

import matplotlib
matplotlib.use("Agg")
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
import pygame

Point = tuple[float, float]


def create_plot_surface(x: Sequence[int], y: Sequence[float], size=(390, 240)) -> pygame.Surface:
    """Cria uma imagem do gráfico; a figura Matplotlib é sempre fechada."""
    fig = Figure(figsize=(size[0] / 100, size[1] / 100), dpi=100)
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_subplot(111)
    ax.plot(x, y, color="#2563eb", linewidth=1.5)
    ax.set_xlabel("Geração")
    ax.set_ylabel("Distância")
    ax.grid(alpha=.2)
    fig.tight_layout()
    canvas.draw()
    surface = pygame.image.frombuffer(canvas.buffer_rgba(), canvas.get_width_height(), "RGBA").copy()
    fig.clear()
    return surface


def draw_plot(screen, x, y, x_label="Geração", y_label="Distância") -> None:
    """Mantém compatibilidade com o código legado."""
    del x_label, y_label
    screen.blit(create_plot_surface(x, y, (400, 400)), (0, 0))


def draw_cities(screen: pygame.Surface, cities_locations: Sequence[Point], rgb_color, node_radius: int) -> None:
    """Desenha as cidades."""
    for city in cities_locations:
        pygame.draw.circle(screen, rgb_color, (round(city[0]), round(city[1])), node_radius)


def draw_paths(screen: pygame.Surface, path: Sequence[Point], rgb_color, width: int = 1) -> None:
    """Desenha uma rota fechada."""
    if len(path) >= 2:
        pygame.draw.lines(screen, rgb_color, True, path, width=width)


def draw_text(screen: pygame.Surface, text: str, color, position=(0, 0), font=None) -> None:
    """Desenha texto sem depender de variáveis globais."""
    selected_font = font or pygame.font.SysFont("Arial", 15)
    screen.blit(selected_font.render(text, True, color), position)
