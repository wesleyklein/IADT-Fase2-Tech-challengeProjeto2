"""Renderer independente dos cálculos de domínio hospitalar."""

import pygame

from domain import DeliveryPriority


COLORS = (
    (37, 99, 235),
    (234, 88, 12),
    (22, 163, 74),
    (147, 51, 234),
    (14, 116, 144),
)

MARKER_RADIUS = 10
SEQUENCE_GAP = 5
SEQUENCE_PADDING_X = 5
SEQUENCE_PADDING_Y = 2
DARK_COLOR = (15, 23, 42)
MARKER_BORDER_COLOR = (30, 41, 59)


class ViewportTransform:
    def __init__(self, points, rect, margin=35):
        xs = [point[0] for point in points] or [0]
        ys = [point[1] for point in points] or [0]
        self.minx = min(xs)
        self.miny = min(ys)

        dx = max(max(xs) - self.minx, 1.0)
        dy = max(max(ys) - self.miny, 1.0)
        scale = min(
            (rect.width - 2 * margin) / dx,
            (rect.height - 2 * margin) / dy,
        )

        self.scale = scale
        self.left = rect.left + margin
        self.bottom = rect.bottom - margin

    def to_screen(self, x, y):
        return (
            round(self.left + (x - self.minx) * self.scale),
            round(self.bottom - (y - self.miny) * self.scale),
        )


def vehicle_color(index):
    if index < len(COLORS):
        return COLORS[index]

    return (
        (index * 83) % 190 + 35,
        (index * 137) % 190 + 35,
        (index * 53) % 190 + 35,
    )


def _draw_centered_text(screen, font, value, color, center):
    text = font.render(str(value), True, color)
    screen.blit(text, text.get_rect(center=center))


def _sequence_badge_rect(text, point, viewport_rect):
    """Posiciona a sequência ao lado do marcador, respeitando a área do mapa."""
    width = text.get_width() + 2 * SEQUENCE_PADDING_X
    height = text.get_height() + 2 * SEQUENCE_PADDING_Y

    x = point[0] + MARKER_RADIUS + SEQUENCE_GAP
    if x + width > viewport_rect.right - 2:
        x = point[0] - MARKER_RADIUS - SEQUENCE_GAP - width

    x = max(viewport_rect.left + 2, min(x, viewport_rect.right - width - 2))
    y = point[1] - height // 2
    y = max(viewport_rect.top + 2, min(y, viewport_rect.bottom - height - 2))

    return pygame.Rect(x, y, width, height)


def _draw_sequence_badge(
    screen,
    font,
    sequence,
    point,
    viewport_rect,
    border_color,
):
    """Desenha a ordem da parada em uma etiqueta externa ao círculo."""
    text = font.render(str(sequence), True, DARK_COLOR)
    badge = _sequence_badge_rect(text, point, viewport_rect)

    pygame.draw.rect(screen, (255, 255, 255), badge, border_radius=4)
    pygame.draw.rect(screen, border_color, badge, 2, border_radius=4)
    screen.blit(text, text.get_rect(center=badge.center))


def draw_hospital_solution(
    screen,
    scenario,
    solution,
    rect,
    font,
    vehicle_id=None,
):
    points = [(scenario.depot.x_km, scenario.depot.y_km)] + [
        (delivery.x_km, delivery.y_km)
        for delivery in scenario.deliveries
    ]
    transform = ViewportTransform(points, rect)

    depot = transform.to_screen(
        scenario.depot.x_km,
        scenario.depot.y_km,
    )
    pygame.draw.rect(
        screen,
        DARK_COLOR,
        pygame.Rect(depot[0] - 9, depot[1] - 9, 18, 18),
        border_radius=3,
    )
    _draw_centered_text(screen, font, "H", (255, 255, 255), depot)

    sequences = {}
    sequence_colors = {}

    for index, route in enumerate(solution.routes):
        if vehicle_id is not None and route.vehicle.id != vehicle_id:
            continue

        color = vehicle_color(index)
        path = [depot] + [
            transform.to_screen(
                stop.delivery.x_km,
                stop.delivery.y_km,
            )
            for stop in route.stops
        ] + [depot]

        if len(path) > 2:
            pygame.draw.lines(screen, color, False, path, 3)

        for stop in route.stops:
            sequences[stop.delivery.id] = stop.sequence
            sequence_colors[stop.delivery.id] = color

    labels = {
        DeliveryPriority.CRITICAL: "C",
        DeliveryPriority.HIGH: "A",
        DeliveryPriority.REGULAR: "R",
    }
    unassigned = {
        item.delivery.id
        for item in solution.unassigned_deliveries
    }

    delivery_points = {}
    for delivery in scenario.deliveries:
        point = transform.to_screen(
            delivery.x_km,
            delivery.y_km,
        )
        delivery_points[delivery.id] = point

        fill_color = (
            (220, 38, 38)
            if delivery.id in unassigned
            else (255, 255, 255)
        )
        pygame.draw.circle(
            screen,
            fill_color,
            point,
            MARKER_RADIUS,
        )
        pygame.draw.circle(
            screen,
            MARKER_BORDER_COLOR,
            point,
            MARKER_RADIUS,
            2,
        )
        _draw_centered_text(
            screen,
            font,
            labels[delivery.priority],
            DARK_COLOR,
            point,
        )

    # Desenha as sequências por último para que a etiqueta fique acima
    # das linhas da rota, mas nunca por cima da letra do marcador.
    for delivery_id, sequence in sequences.items():
        _draw_sequence_badge(
            screen,
            font,
            sequence,
            delivery_points[delivery_id],
            rect,
            sequence_colors[delivery_id],
        )

    legend = [
        "H = Hospital   C = Crítica   A = Alta   R = Regular",
        "Número ao lado = sequência da rota",
        "Vermelho = não atendida",
    ]
    legend += [
        route.vehicle.name
        for route in solution.routes
        if route.stops
    ]

    for index, text_value in enumerate(legend):
        color = (
            DARK_COLOR
            if index < 3
            else vehicle_color(index - 3)
        )
        screen.blit(
            font.render(text_value, True, color),
            (rect.left + 12, rect.top + 10 + index * 20),
        )