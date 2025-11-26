import pygame
import random
import copy
import os
import numpy as np

# --- IMPORTS PARA KERAS ---
try:
    import tensorflow as tf
    from tensorflow import keras
    TF_AVAILABLE = True
except Exception:
    TF_AVAILABLE = False

POBLACION_TAMANO = 30
MUTACION_CHANCE = 0.1
MUTACION_FUERZA = 0.5
SEMILLA_INICIAL = 38

STAGNATION_LIMIT = 10
TRAIN_SAMPLES = 10000
TRAIN_EPOCHS = 10
MODEL_SAVE_PATH = "uma_cerebro_model.h5"

pygame.init()
fuente = pygame.font.SysFont(None, 28)

ANCHO = 800
ALTO = 400
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Uma Musume AI")

NEGRO = (0, 0, 0)
BLANCO = (255, 255, 255)
ROJO = (255, 0, 0)
VERDE = (0, 255, 0)
pygame.mixer.init()
pygame.mixer.music.load("MainMusic.mp3")
pygame.mixer.music.play(-1)
pygame.mixer.music.set_volume(0.5)
clock = pygame.time.Clock()

# Fondo precargado sin operaciones repetidas
try:
    fondo_original = pygame.image.load("fondo.png").convert()
    fondo_original = pygame.transform.scale(fondo_original, (ANCHO, ALTO))
except:
    fondo_original = pygame.Surface((ANCHO, ALTO))
    fondo_original.fill(BLANCO)


# --- CEREBRO ORIGINAL (solo para generar datos entrenados) ---
class Cerebro:
    def __init__(self):
        self.w_ih = [[random.uniform(-1, 1) for _ in range(6)] for _ in range(2)]
        self.w_ho = [random.uniform(-1, 1) for _ in range(6)]
        self.bias_h = [random.uniform(-1, 1) for _ in range(6)]
        self.bias_o = random.uniform(-1, 1)

    def pensar(self, distancia, velocidad):
        inputs = [distancia / ANCHO, velocidad / 20]
        oculta = []
        for i in range(6):
            suma = self.bias_h[i]
            suma += inputs[0] * self.w_ih[0][i]
            suma += inputs[1] * self.w_ih[1][i]
            oculta.append(max(0, suma))
        salida = sum(oculta[i] * self.w_ho[i] for i in range(6))
        salida += self.bias_o
        return salida > 0


# --- UMA CONTROLADA POR MODELO ---
class UmaModelPlayer(pygame.sprite.Sprite):
    def __init__(self, keras_model):
        super().__init__()

        try:
            self.original_image = pygame.image.load("uma.png").convert_alpha()
            self.original_image = pygame.transform.scale(self.original_image, (75, 75))
        except:
            self.original_image = pygame.Surface((75, 75))
            self.original_image.fill(VERDE)

        self.image = self.original_image
        self.rect = self.image.get_rect()
        self.rect.x = 50
        self.rect.y = ALTO - 100
        self.vel_y = 0
        self.en_suelo = True

        self.model = keras_model
        self.predict_fast = keras_model.predict_on_batch

        self.viva = True
        self.fitness = 0

    def update(self, obstaculos, velocidad_juego):
        if not self.viva:
            return

        self.fitness += 1

        distancia_obstaculo = ANCHO
        for obs in obstaculos:
            if obs.rect.right > self.rect.left:
                distancia_obstaculo = obs.rect.x - self.rect.right
                break

        x = np.array([[distancia_obstaculo / ANCHO, velocidad_juego / 20]], dtype=np.float32)
        pred = self.predict_fast(x)[0][0]

        salto = False
        if pred > 0.5 and self.en_suelo:
            self.vel_y = -15
            self.en_suelo = False
            salto = True

        # Marcamos si UMA comenzó un salto
        if salto:
            self.hizo_salto = True
        else:
            self.hizo_salto = False

        # Gravedad
        self.vel_y += 1
        self.rect.y += self.vel_y

        if self.rect.y >= ALTO - 100:
            self.rect.y = ALTO - 100
            self.en_suelo = True

    def get_hitbox(self):
        return self.rect.inflate(-15, -15)


# --- OBSTÁCULO ---
class Obstaculo(pygame.sprite.Sprite):
    def __init__(self, velocidad):
        super().__init__()
        try:
            self.image = pygame.image.load("barrera.png").convert_alpha()
            self.image = pygame.transform.scale(self.image, (75, 75))
        except:
            self.image = pygame.Surface((75, 75))
            self.image.fill(NEGRO)

        self.rect = self.image.get_rect()
        self.rect.x = ANCHO
        self.rect.y = ALTO - 80
        self.velocidad = velocidad

    def update(self):
        self.rect.x -= self.velocidad
        if self.rect.right < 0:
            self.kill()

    def get_hitbox(self):
        return self.rect.inflate(-40, -40)


# --- LOOP DEL JUEGO SOLO MODELO ---
def jugar_con_modelo(model_path=MODEL_SAVE_PATH, seed=None):

    if not TF_AVAILABLE:
        print("TensorFlow no está instalado.")
        return

    if not os.path.exists(model_path):
        print(f"Modelo '{model_path}' no encontrado.")
        return

    model = keras.models.load_model(model_path)
    print("Modelo cargado:", model_path)

    rng = random.Random(seed if seed else SEMILLA_INICIAL)

    obstaculos = pygame.sprite.Group()
    uma = UmaModelPlayer(model)
    grupo_uma = pygame.sprite.Group(uma)

    tiempo_ultimo = 0
    intervalo = rng.randint(900, 1700)

    score = 0
    ejecutando = True
    x_fondo = 0

    # ---- CONTADOR DE SALTOS EFECTIVOS ----
    saltos_efectivos = 0
    obstaculo_anterior = None

    while ejecutando:
        dt = clock.tick(120)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_q:
                pygame.quit(); exit()

        vel_juego = min(25, 10 + score / 1000)
        vel_fondo = vel_juego * 0.6

        tiempo_ultimo += dt
        ultimo = obstaculos.sprites()[-1] if obstaculos else None

        if tiempo_ultimo > intervalo:
            if not ultimo or ultimo.rect.x < ANCHO - 300:
                nuevo_obs = Obstaculo(vel_juego)
                obstaculos.add(nuevo_obs)
                obstaculo_anterior = nuevo_obs
                tiempo_ultimo = 0
                intervalo = rng.randint(
                    max(400, 1500 - score // 2),
                    max(700, 2200 - score // 2)
                )

        x_fondo -= vel_fondo
        if x_fondo <= -ANCHO:
            x_fondo = 0

        uma.update(obstaculos, vel_juego)

        for o in obstaculos:
            o.rect.x -= vel_juego
            if o.rect.right < 0:
                o.kill()

        hitbox_uma = uma.get_hitbox()
        for o in obstaculos:
            if hitbox_uma.colliderect(o.get_hitbox()):
                uma.viva = False
                ejecutando = False

        # ---- DETECCIÓN DE SALTO EFECTIVO ----
        if obstaculo_anterior and uma.viva:
            if obstaculo_anterior.rect.right < uma.rect.left:
                saltos_efectivos += 1
                obstaculo_anterior = None

        pantalla.blit(fondo_original, (x_fondo, 0))
        pantalla.blit(fondo_original, (x_fondo + ANCHO, 0))
        grupo_uma.draw(pantalla)

        for o in obstaculos:
            pantalla.blit(o.image, o.rect)

        pantalla.blit(fuente.render(f"Score: {score}", True, NEGRO), (10, 10))
        pantalla.blit(fuente.render(f"Saltos efectivos: {saltos_efectivos}", True, NEGRO), (10, 40))

        pygame.display.flip()

        score += 1
        if score >= 20000:
            ejecutando = False

    print("Fin del juego. Score:", score)
    print("Saltos efectivos:", saltos_efectivos)
    pygame.quit()


if __name__ == "__main__":
    jugar_con_modelo(MODEL_SAVE_PATH, seed=SEMILLA_INICIAL)


