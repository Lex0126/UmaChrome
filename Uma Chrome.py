import pygame
import random

# Inicializar pygame
pygame.init()

# Tamaño de la pantalla
ANCHO = 800
ALTO = 400
pantalla = pygame.display.set_mode((ANCHO, ALTO))
pygame.display.set_caption("Uma Musume Run")

# Colores
NEGRO = (0, 0, 0)
BLANCO = (255, 255, 255)

# Reloj
clock = pygame.time.Clock()

#Cargar fondo
fondo_original = pygame.image.load("fondo.png").convert()
fondo_original = pygame.transform.scale(fondo_original, (ANCHO, ALTO))
fondo_invertido = pygame.transform.flip(fondo_original, True, False)

#Musica
pygame.mixer.init()
pygame.mixer.music.load("MainMusic.mp3")
pygame.mixer.music.play(-1)
pygame.mixer.music.set_volume(0.5)


# Clase Uma
class Uma(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.image.load("uma.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (75, 75))
        self.rect = self.image.get_rect()
        self.rect.x = 50
        self.rect.y = ALTO - 100
        self.vel_y = 0
        self.en_suelo = True

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] and self.en_suelo:
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
        self.image = pygame.image.load("barrera.png").convert_alpha()
        self.image = pygame.transform.scale(self.image, (75, 75))
        self.rect = self.image.get_rect()
        self.rect.x = ANCHO
        self.rect.y = ALTO - 80
        self.velocidad = velocidad
        self.superado = False

    def update(self):
        self.rect.x -= self.velocidad
        if self.rect.x < -40:
            self.kill()

    def get_hitbox(self):
        return self.rect.inflate(-30, -30)



def jugar():
    x_fondo = 0
    usando_invertido = False
    fondo = fondo_original

    todas = pygame.sprite.Group()
    obstaculos = pygame.sprite.Group()
    uma = Uma()
    todas.add(uma)

    puntuacion = 0
    font = pygame.font.SysFont(None, 36)

    tiempo_ultimo_obstaculo = 0
    intervalo_obstaculos = random.randint(1000, 2000)
    DISTANCIA_MINIMA = 300

    ejecutando = True
    while ejecutando:
        dt = clock.tick(60)  # FPS mas alto = mas fluidez

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()


        vel_juego = 10 + (puntuacion / 8) ** 1#velodidad del juego
        vel_fondo = vel_juego / 1.8


        tiempo_ultimo_obstaculo += dt
        ultimo_obstaculo = obstaculos.sprites()[-1] if obstaculos else None

        if tiempo_ultimo_obstaculo > intervalo_obstaculos:
            puede_generar = False
            if ultimo_obstaculo is None:
                puede_generar = True
            elif ultimo_obstaculo.rect.x < ANCHO - DISTANCIA_MINIMA:
                puede_generar = True

            if puede_generar:
                obstaculo = Obstaculo(vel_juego)
                todas.add(obstaculo)
                obstaculos.add(obstaculo)
                tiempo_ultimo_obstaculo = 0

                min_intervalo = max(300, 1500 - puntuacion // 2)
                max_intervalo = max(600, 2200 - puntuacion // 2)
                intervalo_obstaculos = random.randint(min_intervalo, max_intervalo)


        uma.update()


        for obstaculo in list(obstaculos):
            obstaculo.rect.x -= vel_juego


            if not obstaculo.superado and obstaculo.rect.right < uma.rect.left:
                puntuacion += 10
                obstaculo.superado = True


            if obstaculo.rect.right < 0:
                obstaculo.kill()


        x_fondo -= vel_fondo
        if x_fondo <= -ANCHO:
            x_fondo = 0
            usando_invertido = not usando_invertido
            fondo = fondo_invertido if usando_invertido else fondo_original

        pantalla.blit(fondo, (x_fondo, 0))
        pantalla.blit(fondo_invertido if not usando_invertido else fondo_original,
                      (x_fondo + fondo.get_width(), 0))


        pantalla.blit(uma.image, uma.rect)
        for o in obstaculos:
            pantalla.blit(o.image, o.rect)


        colision = any(uma.get_hitbox().colliderect(o.get_hitbox()) for o in obstaculos)
        if colision:
            ejecutando = False


        texto = font.render(f"Puntuación: {int(puntuacion)}", True, NEGRO)
        pantalla.blit(texto, (10, 10))

        pygame.display.flip()

    return puntuacion






while True:
    puntuacion_final = jugar()

    # Mostrar mensaje de fin
    font = pygame.font.SysFont(None, 48)
    texto_game_over = font.render("Perdiste", True, NEGRO)
    texto_reiniciar = font.render("Presiona R para reiniciar o ESC para salir", True, NEGRO)
    texto_puntuacion = font.render(f"Puntuacion final: {puntuacion_final}", True, NEGRO)

    pantalla.blit(texto_game_over, (ANCHO // 2 - 150, ALTO // 2 - 80))
    pantalla.blit(texto_puntuacion, (ANCHO // 2 - 150, ALTO // 2 - 20))
    pantalla.blit(texto_reiniciar, (ANCHO // 2 - 300, ALTO // 2 + 40))
    pygame.display.flip()


    esperando = True
    while esperando:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    esperando = False
                elif event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    exit()
