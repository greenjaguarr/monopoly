import pygame

BLACK = (0,0,0)
WHITE =(255,255,255)
RED = (255,0,0)
BLUE = (0,0,255)
GREEN=(0,255,0)
YELLOW=(255,255,0)
PURPLE=(255,0,255)
CYAN=(0,255,255)

FPS = 60
pygame.init()

running = True
screen = pygame.display.set_mode((1200, 900))
clock = pygame.time.Clock()

x = 0
y = 0

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
    keys = pygame.key.get_pressed()

    if keys[pygame.K_LEFT]:
        x-=1
    if keys[pygame.K_RIGHT]:
        x+=1
    if keys[pygame.K_UP]:
        y-=1
    if keys[pygame.K_DOWN]:
        y+=1

    screen.fill(BLACK)
    rectangle = pygame.rect.Rect(0 + x,0 + y,100,100)
    
    pygame.draw.rect(screen, RED, rectangle)
    pygame.display.flip()
    clock.tick(FPS)