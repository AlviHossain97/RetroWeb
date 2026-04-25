"""Debug toggles and rendering helpers for AI overlays."""
from __future__ import annotations

import pygame
from ui.fonts import get_font

from settings import TILE_SIZE


class DebugToggles:
    def __init__(self):
        self.show_paths = False
        self.show_heatmap = False
        self.show_labels = False
        self.show_targets = False
        self.show_info = False

    def update_from_input(self, input_handler):
        if input_handler.is_pressed("debug_paths"):
            self.show_paths = not self.show_paths
        if input_handler.is_pressed("debug_heatmap"):
            self.show_heatmap = not self.show_heatmap
        if input_handler.is_pressed("debug_labels"):
            self.show_labels = not self.show_labels
        if input_handler.is_pressed("debug_targets"):
            self.show_targets = not self.show_targets
        if input_handler.is_pressed("debug_info"):
            self.show_info = not self.show_info


def _tile_rect(tile, cam_x, cam_y) -> pygame.Rect:
    return pygame.Rect(tile[0] * TILE_SIZE - cam_x, tile[1] * TILE_SIZE - cam_y, TILE_SIZE, TILE_SIZE)


def draw_distance_heatmap(screen, cam_x, cam_y, field):
    if not field:
        return
    if not field.distances:
        return
    max_dist = max(field.distances.values()) or 1
    overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
    for tile, distance in field.distances.items():
        rect = _tile_rect(tile, cam_x, cam_y)
        alpha = max(20, 150 - int((distance / max_dist) * 110))
        color = (40, 120, 220, alpha)
        overlay.fill(color, rect)
    screen.blit(overlay, (0, 0))


def draw_path(screen, cam_x, cam_y, path, color=(255, 220, 80)):
    if not path or len(path) < 2:
        return
    points = []
    for tile in path:
        points.append((tile[0] * TILE_SIZE + TILE_SIZE // 2 - cam_x, tile[1] * TILE_SIZE + TILE_SIZE // 2 - cam_y))
    pygame.draw.lines(screen, color, False, points, 2)


def draw_target_tile(screen, cam_x, cam_y, tile, color=(80, 220, 255)):
    if not tile:
        return
    rect = _tile_rect(tile, cam_x, cam_y)
    pygame.draw.rect(screen, color, rect, 2)


def draw_actor_label(screen, cam_x, cam_y, actor, text, color=(255, 255, 255)):
    font = get_font(12)
    surf = font.render(text, True, color)
    sx = int((actor.x + 0.5) * TILE_SIZE) - cam_x - surf.get_width() // 2
    sy = int(actor.y * TILE_SIZE) - cam_y - 16
    screen.blit(surf, (sx, sy))


def draw_info_panel(screen, difficulty_label: str, config_text: str):
    font = get_font(14)
    small = get_font(12)
    lines = [difficulty_label, config_text, "F1 paths  F2 heatmap  F3 labels  F4 targets  F5 info"]
    width = max(font.size(lines[0])[0], small.size(lines[1])[0], small.size(lines[2])[0]) + 14
    height = 52
    panel = pygame.Surface((width, height), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 170))
    screen.blit(panel, (8, 60))
    screen.blit(font.render(lines[0], True, (255, 255, 210)), (14, 66))
    screen.blit(small.render(lines[1], True, (180, 220, 255)), (14, 84))
    screen.blit(small.render(lines[2], True, (180, 180, 180)), (14, 100))


def render_ai_debug(screen, cam_x, cam_y, toggles, enemies, boss, field, difficulty_mode):
    if toggles.show_heatmap:
        draw_distance_heatmap(screen, cam_x, cam_y, field)

    actors = list(enemies)
    if boss:
        actors.append(boss)

    if toggles.show_paths:
        for actor in actors:
            draw_path(screen, cam_x, cam_y, getattr(actor, "current_path", []), getattr(actor, "debug_color", (255, 220, 80)))

    if toggles.show_targets:
        for actor in actors:
            draw_target_tile(screen, cam_x, cam_y, getattr(actor, "desired_tile", None), getattr(actor, "debug_color", (80, 220, 255)))

    if toggles.show_labels:
        for actor in actors:
            label = getattr(actor, "state", "")
            draw_actor_label(screen, cam_x, cam_y, actor, label, getattr(actor, "debug_color", (255, 255, 255)))

    if toggles.show_info:
        difficulty_label = f"Difficulty: {difficulty_mode.upper()}"
        config_text = f"Field origin: {field.origin if field else 'n/a'}"
        draw_info_panel(screen, difficulty_label, config_text)
