import pygame
import random
import copy

POBLACION_TAMANO = 30
MUTACION_CHANCE = 0.1
MUTACION_FUERZA = 0.5
SEMILLA_INICIAL = 38

pygame.init()
fuente = pygame.font.SysFont(None, 30)

# Tamaño de la pantalla
ANCHO = 800
ALTO = 400
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Uma Musume AI - Aprendizaje Evolutivo")

# Colores
NEGRO = (0, 0, 0)
BLANCO = (255, 255, 255)
ROJO = (255, 0, 0)
VERDE = (0, 255, 0)

clock = pygame.time.Clock()

try:
    fondo_original = pygame.image.load("fondo.png").convert()
    fondo_original = pygame.transform.scale(fondo_original, (ANCHO, ALTO))
    fondo_invertido = pygame.transform.flip(fondo_original, True, False)
except:
    fondo_original = pygame.Surface((ANCHO, ALTO))
    fondo_original.fill(BLANCO)
    fondo_invertido = fondo_original


    #pygame.mixer.init()
    #pygame.mixer.music.load("MainMusic.mp3")
    #pygame.mixer.music.play(-1)

# --- CLASE CEREBRO (RED NEURONAL SIMPLE) ---
class Cerebro:
    def __init__(self):
        # Arquitectura: 2 Entradas -> 6 Ocultas -> 1 Salida
        # Entradas: [Distancia al obstáculo, Velocidad del juego]

        # Pesos de Entrada a Oculta (2 inputs x 6 neuronas)
        self.w_ih = [[random.uniform(-1, 1) for _ in range(6)] for _ in range(2)]
        # Pesos de Oculta a Salida (6 neuronas x 1 output)
        self.w_ho = [random.uniform(-1, 1) for _ in range(6)]
        # Bias (sesgo)
        self.bias_h = [random.uniform(-1, 1) for _ in range(6)]
        self.bias_o = random.uniform(-1, 1)

    def pensar(self, distancia, velocidad):
        # 1. Normalizar entradas (para que estén entre 0 y 1 aprox)
        inputs = [distancia / ANCHO, velocidad / 20]

        # 2. Procesar Capa Oculta
        oculta = []
        for i in range(6):  # Para cada neurona oculta
            suma = 0
            for j in range(2):  # Sumar inputs * pesos
                suma += inputs[j] * self.w_ih[j][i]
            suma += self.bias_h[i]
            # Función de activación ReLU (si es negativo, se vuelve 0)
            oculta.append(max(0, suma))

            # 3. Procesar Capa de Salida
        suma_salida = 0
        for i in range(6):
            suma_salida += oculta[i] * self.w_ho[i]
        suma_salida += self.bias_o

        # Si la suma es mayor a 0, saltamos
        return suma_salida > 0

    def mutar(self):
        # Modificar ligeramente los pesos para "evolucionar"
        for i in range(len(self.w_ho)):
            if random.random() < MUTACION_CHANCE:
                self.w_ho[i] += random.uniform(-MUTACION_FUERZA, MUTACION_FUERZA)

        for i in range(len(self.w_ih)):
            for j in range(len(self.w_ih[i])):
                if random.random() < MUTACION_CHANCE:
                    self.w_ih[i][j] += random.uniform(-MUTACION_FUERZA, MUTACION_FUERZA)


# --- CLASE UMA MODIFICADA ---
class Uma(pygame.sprite.Sprite):
    def __init__(self, cerebro=None):
        super().__init__()
        try:
            self.original_image = pygame.image.load("uma.png").convert_alpha()
            self.original_image = pygame.transform.scale(self.original_image, (75, 75))
        except:
            self.original_image = pygame.Surface((75, 75))
            self.original_image.fill(ROJO)

        self.image = self.original_image
        self.rect = self.image.get_rect()
        self.rect.x = 50
        self.rect.y = ALTO - 100
        self.vel_y = 0
        self.en_suelo = True

        # IA
        self.cerebro = cerebro if cerebro else Cerebro()
        self.viva = True
        self.fitness = 0  # Puntuacion (tiempo vivo)

    def update(self, obstaculos, velocidad_juego):
        if not self.viva: return

        self.fitness += 1  # Gana puntos por sobrevivir

        # -- VISIÓN DE LA IA --
        # Encontrar el obstáculo más cercano
        distancia_obstaculo = ANCHO  # Por defecto muy lejos
        for obs in obstaculos:
            if obs.rect.right > self.rect.left:  # Si está delante
                distancia_obstaculo = obs.rect.x - self.rect.right
                break

                # -- PENSAR --
        saltar = self.cerebro.pensar(distancia_obstaculo, velocidad_juego)

        if saltar and self.en_suelo:
            self.vel_y = -15
            self.en_suelo = False

        # Gravedad
        self.vel_y += 1
        self.rect.y += self.vel_y

        # Límite del suelo
        if self.rect.y >= ALTO - 100:
            self.rect.y = ALTO - 100
            self.en_suelo = True

    def get_hitbox(self):
        return self.rect.inflate(-15, -15)


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
        if self.rect.x < -100:
            self.kill()

    def get_hitbox(self):
        return self.rect.inflate(-30, -30)


def siguiente_generacion(poblacion_muerta):

    # 1. Selección: Ordenar por fitness (los mejores al final)
    poblacion_muerta.sort(key=lambda x: x.fitness)

    # 2. Elitismo: Guardar al mejor de todos tal cual (Campeón)
    mejor_uma = poblacion_muerta[-1]
    nueva_poblacion = []

    # Clonar al mejor (para asegurar que no perdemos el progreso)
    campeon = Uma(copy.deepcopy(mejor_uma.cerebro))
    nueva_poblacion.append(campeon)

    # 3. Reproducción
    # Usamos los 4 mejores para crear hijos
    padres = poblacion_muerta[-4:]

    while len(nueva_poblacion) < POBLACION_TAMANO:
        # Elegir un padre al azar de los mejores
        padre = random.choice(padres)
        # Crear hijo con una copia del cerebro del padre
        cerebro_hijo = copy.deepcopy(padre.cerebro)
        # Mutar cerebro
        cerebro_hijo.mutar()
        nueva_poblacion.append(Uma(cerebro_hijo))

    return nueva_poblacion


def main():
    generacion_actual = 1
    lista_umas = [Uma() for _ in range(POBLACION_TAMANO)]
    grupo_umas = pygame.sprite.Group()
    for u in lista_umas: grupo_umas.add(u)

    max_puntuacion_historica = 0

    rng_nivel = random.Random()
    semilla_actual = SEMILLA_INICIAL

    while True:
        rng_nivel.seed(semilla_actual)

        obstaculos = pygame.sprite.Group()
        tiempo_ultimo_obstaculo = 0
        intervalo_obstaculos = rng_nivel.randint(1000, 2000)

        puntuacion = 0
        x_fondo = 0
        ejecutando = True

        while ejecutando:
            dt = clock.tick(60)

            for event in pygame.event.get():
                if event.type == pygame.QUIT: pygame.quit(); exit()

            # Lógica de velocidad del juego
            vel_juego = 10 + (puntuacion / 1000)
            if vel_juego > 25: vel_juego = 25
            vel_fondo = vel_juego / 1.8

            tiempo_ultimo_obstaculo += dt
            ultimo_obstaculo = obstaculos.sprites()[-1] if obstaculos else None

            if tiempo_ultimo_obstaculo > intervalo_obstaculos:
                puede_generar = False
                if not ultimo_obstaculo or ultimo_obstaculo.rect.x < ANCHO - 300:
                    puede_generar = True

                if puede_generar:
                    obstaculos.add(Obstaculo(vel_juego))
                    tiempo_ultimo_obstaculo = 0

                    min_int = max(400, 1500 - puntuacion // 2)
                    max_int = max(700, 2200 - puntuacion // 2)
                    intervalo_obstaculos = rng_nivel.randint(min_int, max_int)

            x_fondo -= vel_fondo
            if x_fondo <= -ANCHO: x_fondo = 0

            for uma in lista_umas:
                if uma.viva: uma.update(obstaculos, vel_juego)

            for o in obstaculos:
                o.rect.x -= vel_juego
                if o.rect.right < 0: o.kill()

            vivas_count = 0
            for uma in lista_umas:
                if uma.viva:
                    if any(uma.get_hitbox().colliderect(o.get_hitbox()) for o in obstaculos):
                        uma.viva = False;
                        uma.kill()
                    else:
                        vivas_count += 1

            if vivas_count == 0: ejecutando = False

            # Dibujado
            pantalla.blit(fondo_original, (x_fondo, 0))
            pantalla.blit(fondo_original, (x_fondo + ANCHO, 0))
            grupo_umas.draw(pantalla)
            for o in obstaculos: pantalla.blit(o.image, o.rect)

            info = [
                f"Gen: {generacion_actual} | Seed: {semilla_actual}",
                f"Vivas: {vivas_count}",
                f"Récord: {int(max_puntuacion_historica)}",
                f"Score: {puntuacion}"
            ]
            for i, txt in enumerate(info):
                pantalla.blit(fuente.render(txt, True, (0, 0, 0)), (10, 10 + i * 25))
            pygame.display.flip()
            puntuacion += 1

            if puntuacion >= 5000:
                ejecutando = False

        max_puntuacion_historica = max(max_puntuacion_historica, puntuacion)

        if puntuacion > 2000:
            semilla_actual += 1

        lista_umas = siguiente_generacion(lista_umas)
        grupo_umas.empty()
        for u in lista_umas: grupo_umas.add(u)
        generacion_actual += 1


if __name__ == "__main__":
    main()