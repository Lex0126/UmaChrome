import pygame
import random
import copy
import numpy as np
import os

try:
    from tensorflow import keras

    TF_AVAILABLE = True
except ImportError:
    print("¡ADVERTENCIA! TensorFlow no está instalado.")
    TF_AVAILABLE = False

# --- CONFIGURACIÓN ---
POBLACION_TAMANO = 50
MUTACION_CHANCE = 0.12
MUTACION_FUERZA = 0.5
SEMILLA_INICIAL = 42
FITNESS_META = 50000
SCORE_OBSTACULO = 300

ANCHO = 800
ALTO = 400
ALTURA_PISO = ALTO - 30

pygame.init()
fuente = pygame.font.SysFont(None, 24)
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Hashire Umamusume! - Training Wit...")

NEGRO = (0, 0, 0)
BLANCO = (255, 255, 255)
ROJO = (255, 0, 0)
AZUL = (0, 0, 255)

clock = pygame.time.Clock()

try:
    fondo_original = pygame.image.load("fondo.png").convert()
    fondo_original = pygame.transform.scale(fondo_original, (ANCHO, ALTO))
except:
    fondo_original = pygame.Surface((ANCHO, ALTO))
    fondo_original.fill(BLANCO)


class Cerebro:
    def __init__(self):
        self.input_nodes = 6
        self.hidden_nodes = 8
        self.output_nodes = 1
        self.w_ih = [[random.uniform(-1, 1) for _ in range(self.hidden_nodes)] for _ in range(self.input_nodes)]
        self.w_ho = [random.uniform(-1, 1) for _ in range(self.hidden_nodes)]
        self.bias_h = [random.uniform(-1, 1) for _ in range(self.hidden_nodes)]
        self.bias_o = random.uniform(-1, 1)

    def pensar(self, inputs_list):
        oculta = []
        for i in range(self.hidden_nodes):
            suma = 0
            for j in range(self.input_nodes):
                suma += inputs_list[j] * self.w_ih[j][i]
            suma += self.bias_h[i]
            oculta.append(max(0, suma))
        suma_salida = 0
        for i in range(self.hidden_nodes):
            suma_salida += oculta[i] * self.w_ho[i]
        suma_salida += self.bias_o
        return suma_salida > 0

    def mutar(self):
        for i in range(len(self.w_ho)):
            if random.random() < MUTACION_CHANCE: self.w_ho[i] += random.uniform(-MUTACION_FUERZA, MUTACION_FUERZA)
        for i in range(len(self.w_ih)):
            for j in range(len(self.w_ih[i])):
                if random.random() < MUTACION_CHANCE: self.w_ih[i][j] += random.uniform(-MUTACION_FUERZA,
                                                                                        MUTACION_FUERZA)
        for i in range(len(self.bias_h)):
            if random.random() < MUTACION_CHANCE: self.bias_h[i] += random.uniform(-MUTACION_FUERZA, MUTACION_FUERZA)
        if random.random() < MUTACION_CHANCE: self.bias_o += random.uniform(-MUTACION_FUERZA, MUTACION_FUERZA)


def guardar_mejor_modelo(cerebro_campeon, nombre_archivo="modelo_campeon.h5"):
    if not TF_AVAILABLE: return
    model = keras.Sequential([
        keras.layers.InputLayer(input_shape=(6,)),
        keras.layers.Dense(8, activation='relu'),
        keras.layers.Dense(1, activation='linear')
    ])
    w_ih_np = np.array(cerebro_campeon.w_ih)
    b_h_np = np.array(cerebro_campeon.bias_h)
    w_ho_np = np.array(cerebro_campeon.w_ho).reshape(8, 1)
    b_o_np = np.array([cerebro_campeon.bias_o])
    model.layers[0].set_weights([w_ih_np, b_h_np])
    model.layers[1].set_weights([w_ho_np, b_o_np])
    model.save(nombre_archivo)
    print(f"Modelo guardado en {nombre_archivo}")


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
            self.image.fill(NEGRO)
        self.rect = self.image.get_rect()
        self.rect.x = ANCHO
        self.rect.bottom = ALTURA_PISO
        self.velocidad = velocidad

    def update(self):
        self.rect.x -= self.velocidad
        if self.rect.right < 0: self.kill()

    def get_hitbox(self):
        return self.rect.inflate(-30, -30)


class Uma(pygame.sprite.Sprite):
    def __init__(self, cerebro=None):
        super().__init__()
        try:
            self.image = pygame.image.load("uma.png").convert_alpha()
            self.image = pygame.transform.scale(self.image, (75, 75))
        except:
            self.image = pygame.Surface((75, 75));
            self.image.fill(ROJO)
        self.rect = self.image.get_rect()
        self.rect.x = 50
        self.rect.bottom = ALTURA_PISO
        self.vel_y = 0
        self.en_suelo = True
        self.cerebro = cerebro if cerebro else Cerebro()
        self.viva = True
        self.distancia_viva = 0
        self.obstaculos_saltados = 0
        self.fitness = 0
        self.obstaculos_contados = []

    def update(self, obstaculos, velocidad_juego):
        if not self.viva: return
        self.distancia_viva += 1

        # --- PARTE 1: SCORING (Mirar todo lo que pasa) ---
        for o in obstaculos:
            # Si el obstaculo ya pasó mi lado izquierdo (está detrás)
            if o.rect.right < self.rect.left:
                # Y no lo he contado todavía en MI lista personal
                if o not in self.obstaculos_contados:
                    self.obstaculos_saltados += 1
                    self.obstaculos_contados.append(o)

                    # Limpieza de memoria: Si la lista es muy grande, quitamos los viejos
                    if len(self.obstaculos_contados) > 5:
                        self.obstaculos_contados.pop(0)

        # --- PARTE 2: INPUTS (Mirar solo lo que viene) ---
        obs_siguiente = None
        for o in obstaculos:
            # Buscamos el primero que esté DELANTE
            if o.rect.right > self.rect.left:
                obs_siguiente = o
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

        if self.cerebro.pensar([x1, x2, x3, x4, x5, x6]) and self.en_suelo:
            self.vel_y = -16
            self.en_suelo = False

        self.vel_y += 1.0
        self.rect.y += self.vel_y
        if self.rect.bottom >= ALTURA_PISO:
            self.rect.bottom = ALTURA_PISO
            self.vel_y = 0
            self.en_suelo = True

        # FORMULA DE FITNESS
        self.fitness = self.distancia_viva + (self.obstaculos_saltados * SCORE_OBSTACULO)

    def get_hitbox(self):
        return self.rect.inflate(-15, -15)


def siguiente_generacion(poblacion_muerta):
    poblacion_muerta.sort(key=lambda x: x.fitness)
    mejor_uma = poblacion_muerta[-1]

    # Elitismo: Clonamos al mejor
    nueva_poblacion = [Uma(copy.deepcopy(mejor_uma.cerebro))]

    padres = poblacion_muerta[-6:]
    while len(nueva_poblacion) < POBLACION_TAMANO:
        padre = random.choice(padres)
        cerebro_hijo = copy.deepcopy(padre.cerebro)
        cerebro_hijo.mutar()
        nueva_poblacion.append(Uma(cerebro_hijo))
    return nueva_poblacion, mejor_uma


def main():
    generacion_actual = 1
    lista_umas = [Uma() for _ in range(POBLACION_TAMANO)]
    grupo_umas = pygame.sprite.Group()
    modo_rapido = False
    rng_nivel = random.Random()
    semilla_actual = SEMILLA_INICIAL
    max_fitness_historico = 0
    mejor_cerebro_global = None

    while True:
        rng_nivel.seed(semilla_actual)
        obstaculos = pygame.sprite.Group()
        grupo_umas.empty()
        for u in lista_umas:
            u.rect.bottom = ALTURA_PISO
            u.viva = True
            u.obstaculos_saltados = 0
            u.obstaculos_contados = []
            u.distancia_viva = 0
            grupo_umas.add(u)

        tiempo_ultimo = 0
        intervalo = rng_nivel.randint(1000, 2000)
        distancia_juego = 0
        x_fondo = 0
        ejecutando = True

        while ejecutando:
            dt = 16 if modo_rapido else clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_TAB: modo_rapido = not modo_rapido
                    if event.key == pygame.K_s and mejor_cerebro_global:
                        guardar_mejor_modelo(mejor_cerebro_global, "modelo_manual.h5")

            vel_juego = 10 + (distancia_juego / 1000)
            if vel_juego > 25: vel_juego = 25

            tiempo_ultimo += dt
            ultimo = obstaculos.sprites()[-1] if obstaculos else None

            if tiempo_ultimo > intervalo:
                safe = True
                if ultimo and ultimo.rect.right > ANCHO - 300: safe = False
                if safe:
                    obstaculos.add(Obstaculo(vel_juego))
                    tiempo_ultimo = 0
                    intervalo = rng_nivel.randint(800, 2200)

            vivas_count = 0
            mejor_fitness_actual = 0
            mejor_obs_actual = 0

            for uma in lista_umas:
                if uma.viva:
                    uma.update(obstaculos, vel_juego)

                    if uma.fitness > mejor_fitness_actual:
                        mejor_fitness_actual = uma.fitness
                        mejor_obs_actual = uma.obstaculos_saltados

                    if any(uma.get_hitbox().colliderect(o.get_hitbox()) for o in obstaculos):
                        uma.viva = False;
                        uma.kill()
                    else:
                        vivas_count += 1

            obstaculos.update()
            x_fondo -= vel_juego * 0.5
            if x_fondo <= -ANCHO: x_fondo = 0
            if vivas_count == 0: ejecutando = False

            if not modo_rapido or distancia_juego % 5 == 0:
                pantalla.blit(fondo_original, (x_fondo, 0))
                pantalla.blit(fondo_original, (x_fondo + ANCHO, 0))
                grupo_umas.draw(pantalla)
                for o in obstaculos: pantalla.blit(o.image, o.rect)

                info = [
                    f"Gen: {generacion_actual} | Vivas: {vivas_count}",
                    f"Récord Global: {int(max_fitness_historico)}",
                    f"Score Líder: {int(mejor_fitness_actual)}",
                    f"Obs. Líder: {mejor_obs_actual}",
                    f"Modo Rápido (TAB): {'ON' if modo_rapido else 'OFF'}"
                ]
                for i, txt in enumerate(info):
                    pantalla.blit(fuente.render(txt, True, NEGRO), (10, 10 + i * 20))
                pygame.display.flip()

            distancia_juego += 1
            if mejor_fitness_actual > FITNESS_META + 2000: ejecutando = False

        lista_umas, mejor_de_gen = siguiente_generacion(lista_umas)
        if mejor_de_gen.fitness > max_fitness_historico:
            max_fitness_historico = mejor_de_gen.fitness
            mejor_cerebro_global = mejor_de_gen.cerebro
            if max_fitness_historico >= FITNESS_META:
                print(f"\n🏆 OBJETIVO ALCANZADO! Fitness: {max_fitness_historico}")
                guardar_mejor_modelo(mejor_cerebro_global, "modelo_campeon.h5")
                pygame.quit();
                exit()
            if max_fitness_historico > 5000: semilla_actual += 1
        print(
            f"Gen {generacion_actual} | Mejor Score: {int(mejor_de_gen.fitness)} | Obs: {mejor_de_gen.obstaculos_saltados}")
        generacion_actual += 1


if __name__ == "__main__":
    main()