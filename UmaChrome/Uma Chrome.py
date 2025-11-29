import pygame
import random

# --- CONFIGURACIÓN ---
ANCHO = 800
ALTO = 400
ALTURA_PISO = ALTO - 30
SCORE_OBSTACULO = 300

pygame.init()
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Hashire Umamusume! - Manual")
clock = pygame.time.Clock()
fuente = pygame.font.SysFont(None, 30)

# Colores
NEGRO = (0, 0, 0)
BLANCO = (255, 255, 255)
ROJO = (255, 0, 0)

# Cargar recursos
try:
    fondo_original = pygame.image.load("fondo.png").convert()
    fondo_original = pygame.transform.scale(fondo_original, (ANCHO, ALTO))
except:
    fondo_original = pygame.Surface((ANCHO, ALTO))
    fondo_original.fill(BLANCO)


class Uma(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        try:
            self.image = pygame.image.load("uma.png").convert_alpha()
            self.image = pygame.transform.scale(self.image, (75, 75))
        except:
            self.image = pygame.Surface((75, 75))
            self.image.fill(ROJO)
        self.rect = self.image.get_rect()
        self.rect.x = 50
        self.rect.bottom = ALTURA_PISO
        self.vel_y = 0
        self.en_suelo = True

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] and self.en_suelo:
            self.vel_y = -16
            self.en_suelo = False

        self.vel_y += 1.0
        self.rect.y += self.vel_y

        if self.rect.bottom >= ALTURA_PISO:
            self.rect.bottom = ALTURA_PISO
            self.en_suelo = True

    def get_hitbox(self):
        return self.rect.inflate(-15, -15)


class Obstaculo(pygame.sprite.Sprite):
    def __init__(self, velocidad):
        super().__init__()
        TIPOS = [
            {"img": "ObstaculoNormal.png", "dim": (45, 55)},
            {"img": "ObstaculoAlto.png", "dim": (45, 85)},
            {"img": "ObstaculoAncho.png", "dim": (120, 50)}
        ]
        tipo = random.choice(TIPOS)
        self.width, self.height = tipo["dim"]

        try:
            self.image = pygame.image.load(tipo["img"]).convert_alpha()
            self.image = pygame.transform.scale(self.image, (self.width, self.height))
        except:
            self.image = pygame.Surface((self.width, self.height))
            self.image.fill(NEGRO)

        self.rect = self.image.get_rect()
        self.rect.x = ANCHO
        self.rect.bottom = ALTURA_PISO
        self.velocidad = velocidad
        self.superado = False  # Importante para el conteo

    def update(self):
        self.rect.x -= self.velocidad
        if self.rect.right < 0:
            self.kill()

    def get_hitbox(self):
        return self.rect.inflate(-30, -30)


def jugar():
    uma = Uma()
    obstaculos = pygame.sprite.Group()

    distancia = 0
    obs_evitados = 0
    score_total = 0

    x_fondo = 0
    tiempo_ultimo = 0
    intervalo = random.randint(1000, 2000)

    ejecutando = True
    while ejecutando:
        dt = clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                exit()

        # Velocidad basada en distancia recorrida
        vel_juego = 10 + (distancia / 1000)
        if vel_juego > 25: vel_juego = 25

        tiempo_ultimo += dt
        ultimo = obstaculos.sprites()[-1] if obstaculos else None

        if tiempo_ultimo > intervalo:
            safe = True
            if ultimo and ultimo.rect.right > ANCHO - 300: safe = False
            if safe:
                obstaculos.add(Obstaculo(vel_juego))
                tiempo_ultimo = 0
                intervalo = random.randint(800, 2200)

        uma.update()
        obstaculos.update()

        # Lógica de choque y superación
        hitbox_uma = uma.get_hitbox()
        for o in obstaculos:
            if hitbox_uma.colliderect(o.get_hitbox()):
                ejecutando = False  # Game Over

            # Contar obstáculo si ya pasó a Uma y no ha sido contado
            if not o.superado and o.rect.right < uma.rect.left:
                o.superado = True
                obs_evitados += 1

        # Fondo
        x_fondo -= vel_juego * 0.5
        if x_fondo <= -ANCHO: x_fondo = 0
        pantalla.blit(fondo_original, (x_fondo, 0))
        pantalla.blit(fondo_original, (x_fondo + ANCHO, 0))

        # Dibujar
        pantalla.blit(uma.image, uma.rect)
        for o in obstaculos:
            pantalla.blit(o.image, o.rect)

        # CALCULO DE SCORE ESTANDARIZADO
        distancia += 1
        score_total = distancia + (obs_evitados * SCORE_OBSTACULO)

        # Mostrar HUD
        txt_score = fuente.render(f"Score: {score_total}", True, NEGRO)
        txt_obs = fuente.render(f"Obstáculos: {obs_evitados}", True, NEGRO)
        pantalla.blit(txt_score, (10, 10))
        pantalla.blit(txt_obs, (10, 40))

        pygame.display.flip()

    return score_total, obs_evitados


while True:
    score_final, obs_total = jugar()

    # Pantalla Game Over
    pantalla.fill(BLANCO)
    txt_go = fuente.render("¡PERDISTE!", True, ROJO)
    txt_res = fuente.render(f"Score Final: {score_final}", True, NEGRO)
    txt_obs = fuente.render(f"Obstáculos Superados: {obs_total}", True, NEGRO)
    txt_rst = fuente.render("Presiona R para reiniciar", True, NEGRO)

    pantalla.blit(txt_go, (ANCHO // 2 - 50, ALTO // 2 - 60))
    pantalla.blit(txt_res, (ANCHO // 2 - 80, ALTO // 2 - 20))
    pantalla.blit(txt_obs, (ANCHO // 2 - 100, ALTO // 2 + 10))
    pantalla.blit(txt_rst, (ANCHO // 2 - 120, ALTO // 2 + 50))
    pygame.display.flip()

    esperando = True
    while esperando:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                esperando = False