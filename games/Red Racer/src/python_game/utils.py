import pygame
import os
from settings import RED

def load_image(path, width, height):
    """
    Load an image safely from the path.
    Returns a colored surface placeholder if loading fails.
    """
    try:
        if not os.path.exists(path):
             return None
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (width, height))
    except (pygame.error, FileNotFoundError):
        # Return none or a placeholder?
        # Returning a placeholder surface is safer for the game loop
        surf = pygame.Surface((width, height))
        surf.fill(RED) 
        return surf
