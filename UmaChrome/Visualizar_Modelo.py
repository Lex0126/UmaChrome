import pygame
import random
import numpy as np
import os
import time

try:
    import tensorflow as tf
    from tensorflow import keras

    print("TensorFlow importado correctamente.")
except ImportError:
    print("ERROR: Necesitas TensorFlow instalado.")
    exit()

# CONFIGURACIÓN
MODEL_PATH = "modelo_campeon.h5"
ANCHO = 800
ALTO = 400
ALTURA_PISO = ALTO - 25
SCORE_OBSTACULO = 300

pygame.init()
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Hashire Umamusume! - Automatico")
fuente = pygame.font.SysFont(None, 30)
clock = pygame.time.Clock()

try:
    fondo_original = pygame.image.load("fondo.png").convert()
    fondo_original = pygame.transform.scale(fondo_original, (ANCHO, ALTO))
except:
    fondo_original = pygame.Surface((ANCHO, ALTO));
    fondo_original.fill((255, 255, 255))


class UmaPlayer(pygame.sprite.Sprite):
    def __init__(self, model):
        super().__init__()
        try:
            self.image = pygame.image.load("uma.png").convert_alpha()
            self.image = pygame.transform.scale(self.image, (75, 75))
        except:
            self.image = pygame.Surface((75, 75));
            self.image.fill((255, 0, 0))
        self.rect = self.image.get_rect()
        self.rect.x = 50
        self.rect.bottom = ALTURA_PISO
        self.vel_y = 0
        self.en_suelo = True
        self.model = model
        self.viva = True

    def update(self, obstaculos, velocidad_juego):
        if not self.viva: return
        obs_siguiente = None
        for o in obstaculos:
            if o.rect.right > self.rect.left:
                obs_siguiente = o;
                break

        dist_obs, ancho_obs, alto_obs = ANCHO, 0, 0
        if obs_siguiente:
            dist_obs = obs_siguiente.rect.x - self.rect.right
            ancho_obs = obs_siguiente.width
            alto_obs = obs_siguiente.height

        x1 = (ALTURA_PISO - self.rect.bottom) / 200.0
        x2 = dist_obs / ANCHO
        x3 = ancho_obs / 150.0
        x4 = alto_obs / 150.0
        x5 = self.vel_y / 20.0
        x6 = velocidad_juego / 30.0

        entrada = tf.constant([[x1, x2, x3, x4, x5, x6]], dtype=tf.float32)
        prediccion = self.model(entrada, training=False).numpy()[0][0]

        if prediccion > 0 and self.en_suelo:
            self.vel_y = -16
            self.en_suelo = False
        self.vel_y += 1.0
        self.rect.y += self.vel_y
        if self.rect.bottom >= ALTURA_PISO:
            self.rect.bottom = ALTURA_PISO
            self.vel_y = 0
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
            self.image = pygame.Surface((self.width, self.height));
            self.image.fill((0, 0, 0))
        self.rect = self.image.get_rect()
        self.rect.x = ANCHO
        self.rect.bottom = ALTURA_PISO
        self.velocidad = velocidad
        self.superado = False

    def update(self):
        self.rect.x -= self.velocidad
        if self.rect.right < 0: self.kill()

    def get_hitbox(self):
        return self.rect.inflate(-30, -30)


def main():
    if not os.path.exists(MODEL_PATH):
        print(f"¡ARCHIVO {MODEL_PATH} NO ENCONTRADO!")
        return

    print(f"Cargando modelo: {MODEL_PATH}")
    model = keras.models.load_model(MODEL_PATH)
    dummy_input = tf.constant([[0.0] * 6], dtype=tf.float32)
    model(dummy_input, training=False)
    print("Modelo Cargado")

    player = UmaPlayer(model)
    obstaculos = pygame.sprite.Group()

    distancia = 0  # Score de tiempo
    obs_evitados = 0
    score_total = 0

    x_fondo = 0
    rng = random.Random()
    tiempo_ultimo = 0
    intervalo = 1500

    ejecutando = True
    while ejecutando:
        dt = clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT: ejecutando = False

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
                intervalo = rng.randint(800, 2200)

        if player.viva:
            player.update(obstaculos, vel_juego)
            hitbox = player.get_hitbox()
            for o in obstaculos:
                if hitbox.colliderect(o.get_hitbox()):
                    player.viva = False
                    print(f"Juego terminado. Score final: {int(score_total)}")

                # LOGICA DE CONTEO (Igual que en Manual)
                if not o.superado and o.rect.right < player.rect.left:
                    o.superado = True
                    obs_evitados += 1

        obstaculos.update()
        x_fondo -= vel_juego * 0.5
        if x_fondo <= -ANCHO: x_fondo = 0

        pantalla.blit(fondo_original, (x_fondo, 0))
        pantalla.blit(fondo_original, (x_fondo + ANCHO, 0))
        if player.viva: pantalla.blit(player.image, player.rect)
        for o in obstaculos: pantalla.blit(o.image, o.rect)

        # CALCULO Y DISPLAY
        if player.viva:
            distancia += 1
            score_total = distancia + (obs_evitados * SCORE_OBSTACULO)

        txt_score = fuente.render(f"Score: {int(score_total)}", True, (0, 0, 0))
        txt_obs = fuente.render(f"Obstáculos: {obs_evitados}", True, (0, 0, 0))
        pantalla.blit(txt_score, (10, 10))
        pantalla.blit(txt_obs, (10, 40))

        if not player.viva:
            over = fuente.render("GAME OVER - ESC para salir", True, (255, 0, 0))
            pantalla.blit(over, (ANCHO // 2 - 150, ALTO // 2))
            keys = pygame.key.get_pressed()
            if keys[pygame.K_ESCAPE]: ejecutando = False

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()