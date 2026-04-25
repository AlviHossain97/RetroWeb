import pygame
import os

pygame.init()
pygame.display.set_mode((100, 100)) # Init display for image loading

files = ["Road.png", "Road2.png", "Road3.png", "Road4.png"]
base_dir = r"c:\Users\alvi9\MyWork\Testing"

for f in files:
    path = os.path.join(base_dir, f)
    if os.path.exists(path):
        img = pygame.image.load(path)
        print(f"{f}: {img.get_width()} x {img.get_height()}")
    else:
        print(f"{f}: Not Found")
