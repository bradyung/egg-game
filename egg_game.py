import math
import random
import sys
import pygame

pygame.init()

WIDTH = 1100
HEIGHT = 700
FPS = 60

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Egg Balance Rover")

CLOCK = pygame.time.Clock()

FONT = pygame.font.SysFont("arial", 28)
BIG_FONT = pygame.font.SysFont("arial", 54, bold=True)
SMALL_FONT = pygame.font.SysFont("arial", 22)

SKY = (150, 210, 255)
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
GREEN = (70, 155, 70)
DARK_GREEN = (45, 110, 45)
BROWN = (120, 85, 45)
RED = (200, 70, 70)
DARK_RED = (150, 40, 40)
GRAY = (80, 80, 80)
LIGHT_GRAY = (190, 190, 190)
YELLOW = (245, 205, 60)
EGG = (245, 235, 210)
EGG_LINE = (140, 100, 70)
BLUE = (60, 90, 220)

GROUND_BASE = 520

CAR_WIDTH = 90
CAR_HEIGHT = 28
WHEEL_RADIUS = 16

ACCEL = 0.28
FRICTION = 0.96
MAX_SPEED = 6.0
GRAVITY = 0.45

EGG_STIFFNESS = 0.035
EGG_DAMPING = 0.93
FAIL_ANGLE = 1.28

camera_x = 0.0


def get_ground_y(x: float) -> float:
    return (
        GROUND_BASE
        + 55 * math.sin(x * 0.008)
        + 28 * math.sin(x * 0.021)
        + 10 * math.sin(x * 0.055)
    )


def get_slope_angle(x: float) -> float:
    left = get_ground_y(x - 3)
    right = get_ground_y(x + 3)
    return math.atan2(right - left, 6)


class Particle:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3.5, 3.5)
        self.vy = random.uniform(-6.5, -2.5)
        self.life = random.randint(25, 45)
        self.radius = random.randint(2, 5)

    def update(self):
        self.vy += 0.2
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surface):
        if self.life > 0:
            pygame.draw.circle(surface, EGG, (int(self.x), int(self.y)), self.radius)
            pygame.draw.circle(surface, EGG_LINE, (int(self.x), int(self.y)), self.radius, 1)


class Game:
    def __init__(self):
        self.reset()

    def reset(self):
        self.car_x = 180.0
        self.car_vx = 0.0
        self.left_pressed = False
        self.right_pressed = False

        self.egg_angle = 0.0
        self.egg_angular_velocity = 0.0

        self.egg_falling = False
        self.egg_broken = False
        self.egg_x = 0.0
        self.egg_y = 0.0
        self.egg_vx = 0.0
        self.egg_vy = 0.0

        self.score = 0.0
        self.best_distance = 0.0
        self.game_over = False
        self.particles = []

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_a, pygame.K_LEFT):
                self.left_pressed = True
            if event.key in (pygame.K_d, pygame.K_RIGHT):
                self.right_pressed = True
            if event.key == pygame.K_r and self.game_over:
                self.reset()

        if event.type == pygame.KEYUP:
            if event.key in (pygame.K_a, pygame.K_LEFT):
                self.left_pressed = False
            if event.key in (pygame.K_d, pygame.K_RIGHT):
                self.right_pressed = False

    def update(self):
        global camera_x

        if not self.game_over:
            if self.left_pressed:
                self.car_vx -= ACCEL
            if self.right_pressed:
                self.car_vx += ACCEL

            self.car_vx *= FRICTION
            self.car_vx = max(-MAX_SPEED, min(MAX_SPEED, self.car_vx))
            self.car_x += self.car_vx

            if self.car_x < 120:
                self.car_x = 120
                self.car_vx = 0

            slope = get_slope_angle(self.car_x)

            target_egg = -slope * 1.25 - self.car_vx * 0.055
            torque = (target_egg - self.egg_angle) * EGG_STIFFNESS

            self.egg_angular_velocity += torque
            self.egg_angular_velocity *= EGG_DAMPING
            self.egg_angle += self.egg_angular_velocity

            self.score = max(self.score, self.car_x - 180)
            self.best_distance = self.score

            if abs(self.egg_angle) > FAIL_ANGLE:
                self.start_egg_fall()

        else:
            if self.egg_falling:
                self.egg_vy += GRAVITY
                self.egg_x += self.egg_vx
                self.egg_y += self.egg_vy

                ground_y = get_ground_y(self.egg_x)
                if self.egg_y + 12 >= ground_y:
                    self.egg_y = ground_y - 12
                    self.egg_falling = False
                    self.egg_broken = True
                    self.make_egg_particles()

        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

        target_camera = self.car_x - 250
        camera_x += (target_camera - camera_x) * 0.08

    def start_egg_fall(self):
        self.game_over = True
        self.egg_falling = True

        car_top_x, car_top_y = self.get_car_top_center()

        self.egg_x = car_top_x + math.sin(self.egg_angle) * 18
        self.egg_y = car_top_y - 16
        self.egg_vx = self.car_vx * 1.2 + math.sin(self.egg_angle) * 2.2
        self.egg_vy = -2.0

    def make_egg_particles(self):
        for _ in range(18):
            self.particles.append(Particle(self.egg_x, self.egg_y))

    def get_car_top_center(self):
        ground_y = get_ground_y(self.car_x)
        body_y = ground_y - 42
        return self.car_x, body_y - 2

    def draw_background(self, surface):
        surface.fill(SKY)
        pygame.draw.circle(surface, YELLOW, (930, 110), 55)
        pygame.draw.circle(surface, WHITE, (180, 120), 35)
        pygame.draw.circle(surface, WHITE, (220, 105), 28)
        pygame.draw.circle(surface, WHITE, (255, 120), 32)
        pygame.draw.circle(surface, WHITE, (560, 150), 30)
        pygame.draw.circle(surface, WHITE, (595, 136), 24)
        pygame.draw.circle(surface, WHITE, (628, 150), 28)

    def draw_ground(self, surface):
        points = []
        for sx in range(-20, WIDTH + 20, 8):
            world_x = sx + camera_x
            world_y = get_ground_y(world_x)
            points.append((sx, world_y))

        points.append((WIDTH + 20, HEIGHT))
        points.append((-20, HEIGHT))

        pygame.draw.polygon(surface, GREEN, points)

        top_points = points[:-2]
        if len(top_points) >= 2:
            pygame.draw.lines(surface, DARK_GREEN, False, top_points, 4)

    def draw_car(self, surface):
        ground_y = get_ground_y(self.car_x)
        slope = get_slope_angle(self.car_x)

        screen_x = self.car_x - camera_x
        body_y = ground_y - 42
        body_center = (screen_x, body_y)

        car_surface = pygame.Surface((160, 120), pygame.SRCALPHA)
        cx = 80
        cy = 60

        body_rect = pygame.Rect(cx - CAR_WIDTH // 2, cy - CAR_HEIGHT // 2, CAR_WIDTH, CAR_HEIGHT)
        top_rect = pygame.Rect(cx - 18, cy - 28, 42, 18)

        pygame.draw.rect(car_surface, RED, body_rect, border_radius=8)
        pygame.draw.rect(car_surface, DARK_RED, body_rect, 3, border_radius=8)
        pygame.draw.rect(car_surface, RED, top_rect, border_radius=6)
        pygame.draw.rect(car_surface, DARK_RED, top_rect, 3, border_radius=6)

        left_wheel = (cx - 25, cy + 16)
        right_wheel = (cx + 25, cy + 16)

        pygame.draw.circle(car_surface, BLACK, left_wheel, WHEEL_RADIUS)
        pygame.draw.circle(car_surface, BLACK, right_wheel, WHEEL_RADIUS)
        pygame.draw.circle(car_surface, LIGHT_GRAY, left_wheel, 7)
        pygame.draw.circle(car_surface, LIGHT_GRAY, right_wheel, 7)

        rotated = pygame.transform.rotate(car_surface, -math.degrees(slope))
        rect = rotated.get_rect(center=(int(body_center[0]), int(body_center[1])))
        surface.blit(rotated, rect)

        if not self.egg_broken:
            self.draw_egg(surface, screen_x, body_y, slope)

    def draw_egg(self, surface, screen_x, body_y, slope):
        if self.egg_falling:
            egg_rect = pygame.Rect(0, 0, 20, 26)
            egg_rect.center = (int(self.egg_x - camera_x), int(self.egg_y))
            pygame.draw.ellipse(surface, EGG, egg_rect)
            pygame.draw.ellipse(surface, EGG_LINE, egg_rect, 2)
            return

        egg_surface = pygame.Surface((70, 70), pygame.SRCALPHA)
        egg_rect = pygame.Rect(25, 18, 20, 26)
        pygame.draw.ellipse(egg_surface, EGG, egg_rect)
        pygame.draw.ellipse(egg_surface, EGG_LINE, egg_rect, 2)

        total_angle = -(math.degrees(slope) + math.degrees(self.egg_angle))
        rotated_egg = pygame.transform.rotate(egg_surface, total_angle)
        rotated_rect = rotated_egg.get_rect(center=(int(screen_x), int(body_y - 28)))
        surface.blit(rotated_egg, rotated_rect)

    def draw_broken_egg(self, surface):
        if not self.egg_broken:
            return

        sx = int(self.egg_x - camera_x)
        sy = int(self.egg_y)

        pygame.draw.ellipse(surface, YELLOW, (sx - 12, sy - 4, 24, 12))
        pygame.draw.polygon(surface, EGG, [(sx - 20, sy + 2), (sx - 8, sy - 10), (sx - 3, sy + 5)])
        pygame.draw.polygon(surface, EGG, [(sx + 20, sy + 2), (sx + 8, sy - 10), (sx + 3, sy + 5)])
        pygame.draw.polygon(surface, EGG_LINE, [(sx - 20, sy + 2), (sx - 8, sy - 10), (sx - 3, sy + 5)], 2)
        pygame.draw.polygon(surface, EGG_LINE, [(sx + 20, sy + 2), (sx + 8, sy - 10), (sx + 3, sy + 5)], 2)

    def draw_particles(self, surface):
        for p in self.particles:
            p.draw(surface)

    def draw_hud(self, surface):
        score_text = FONT.render(f"Distance: {int(self.best_distance)}", True, BLACK)
        speed_text = SMALL_FONT.render(f"Speed: {self.car_vx:.1f}", True, BLACK)

        balance_ratio = 1.0 - min(1.0, abs(self.egg_angle) / FAIL_ANGLE)
        balance_percent = int(balance_ratio * 100)

        balance_text = SMALL_FONT.render(f"Balance: {balance_percent}%", True, BLACK)

        surface.blit(score_text, (25, 20))
        surface.blit(speed_text, (25, 60))
        surface.blit(balance_text, (25, 90))

        pygame.draw.rect(surface, BLACK, (25, 125, 220, 24), 2)
        pygame.draw.rect(surface, BLUE, (27, 127, int(216 * balance_ratio), 20))

        controls = SMALL_FONT.render("A/D or Arrow Keys to drive", True, BLACK)
        surface.blit(controls, (25, 160))

    def draw_game_over(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, (0, 0))

        title = BIG_FONT.render("Game Over", True, WHITE)
        msg1 = FONT.render("The egg fell off the rover.", True, WHITE)
        msg2 = FONT.render(f"Distance: {int(self.best_distance)}", True, WHITE)
        msg3 = SMALL_FONT.render("Press R to restart", True, WHITE)

        surface.blit(title, title.get_rect(center=(WIDTH // 2, 240)))
        surface.blit(msg1, msg1.get_rect(center=(WIDTH // 2, 310)))
        surface.blit(msg2, msg2.get_rect(center=(WIDTH // 2, 355)))
        surface.blit(msg3, msg3.get_rect(center=(WIDTH // 2, 405)))

    def draw(self, surface):
        self.draw_background(surface)
        self.draw_ground(surface)
        self.draw_car(surface)
        self.draw_broken_egg(surface)
        self.draw_particles(surface)
        self.draw_hud(surface)

        if self.game_over:
            self.draw_game_over(surface)


def draw_start_screen():
    SCREEN.fill(SKY)

    title = BIG_FONT.render("Egg Balance Rover", True, BLACK)
    subtitle = FONT.render("Drive over hills without letting the egg fall.", True, BLACK)
    controls1 = SMALL_FONT.render("A / D or Left / Right Arrow Keys to move", True, BLACK)
    controls2 = SMALL_FONT.render("Press SPACE to start", True, BLACK)

    pygame.draw.circle(SCREEN, YELLOW, (930, 110), 55)

    pygame.draw.rect(SCREEN, RED, (455, 355, 150, 35), border_radius=10)
    pygame.draw.circle(SCREEN, BLACK, (490, 405), 18)
    pygame.draw.circle(SCREEN, BLACK, (570, 405), 18)
    pygame.draw.circle(SCREEN, LIGHT_GRAY, (490, 405), 8)
    pygame.draw.circle(SCREEN, LIGHT_GRAY, (570, 405), 8)
    pygame.draw.ellipse(SCREEN, EGG, (520, 320, 26, 34))
    pygame.draw.ellipse(SCREEN, EGG_LINE, (520, 320, 26, 34), 2)

    SCREEN.blit(title, title.get_rect(center=(WIDTH // 2, 140)))
    SCREEN.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 210)))
    SCREEN.blit(controls1, controls1.get_rect(center=(WIDTH // 2, 520)))
    SCREEN.blit(controls2, controls2.get_rect(center=(WIDTH // 2, 560)))


def main():
    global camera_x
    game = Game()

    state = "start"

    while True:
        CLOCK.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if state == "start":
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    game.reset()
                    camera_x = 0
                    state = "play"
            else:
                game.handle_event(event)

        if state == "start":
            draw_start_screen()
        else:
            game.update()
            game.draw(SCREEN)

        pygame.display.flip()


if __name__ == "__main__":
    main()