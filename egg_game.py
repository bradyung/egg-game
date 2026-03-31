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
RED = (200, 70, 70)
DARK_RED = (150, 40, 40)
LIGHT_GRAY = (190, 190, 190)
YELLOW = (245, 205, 60)
EGG = (245, 235, 210)
EGG_LINE = (140, 100, 70)
BLUE = (60, 90, 220)
BASKET = (160, 105, 60)
BASKET_DARK = (110, 70, 35)
ORANGE = (245, 150, 60)

GROUND_BASE = 520

CAR_WIDTH = 90
CAR_HEIGHT = 28
WHEEL_RADIUS = 16

ACCEL = 0.24
FRICTION = 0.965
BASE_MAX_SPEED = 4.5

GRAVITY = 0.55
EGG_GRAVITY = 0.42

START_FLAT_DISTANCE = 700
TRANSITION_DISTANCE = 260

BASKET_HALF_WIDTH = 18
BASKET_WALL_HEIGHT = 9
BASKET_FLOOR_THICKNESS = 7

EGG_RADIUS_X = 10
EGG_RADIUS_Y = 13
EGG_ROLL_DAMPING = 0.992
EGG_WALL_BOUNCE = 0.78

TIP_FAIL_ANGLE = math.radians(30)

CAR_BOUNCE_DAMPING = 0.25
CAR_ANGULAR_DAMPING = 0.90
CAR_ANGLE_SPRING = 0.16
CAR_AIR_ROTATION = 0.0014

camera_x = 0.0


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def smoothstep(edge0: float, edge1: float, x: float) -> float:
    if edge1 == edge0:
        return 1.0
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def get_difficulty_from_x(x: float) -> float:
    return clamp((x - 180.0) / 2400.0, 0.0, 1.0)


def get_ground_y(x: float) -> float:
    difficulty = get_difficulty_from_x(x)

    amp1 = lerp(18, 55, difficulty)
    amp2 = lerp(8, 28, difficulty)
    amp3 = lerp(3, 10, difficulty)

    hills = (
        GROUND_BASE
        + amp1 * math.sin(x * 0.008)
        + amp2 * math.sin(x * 0.021)
        + amp3 * math.sin(x * 0.055)
    )

    blend = smoothstep(START_FLAT_DISTANCE, START_FLAT_DISTANCE + TRANSITION_DISTANCE, x)
    return lerp(GROUND_BASE, hills, blend)


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
        self.car_y = get_ground_y(self.car_x) - 42
        self.car_vx = 0.0
        self.car_vy = 0.0
        self.prev_car_vx = 0.0

        self.car_angle = 0.0
        self.car_angular_velocity = 0.0

        self.left_pressed = False
        self.right_pressed = False

        self.egg_offset = 0.0
        self.egg_roll_v = 0.0

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

        self.difficulty = 0.0
        self.max_speed = BASE_MAX_SPEED

        self.wobble_flash_timer = 0
        self.big_wobble_flash_timer = 0

        self.start_grace_distance = 260
        self.start_grace_timer = FPS * 3

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

    def update_car_physics(self):
        self.difficulty = get_difficulty_from_x(self.car_x)
        self.max_speed = lerp(BASE_MAX_SPEED, 6.7, self.difficulty)
        accel_now = lerp(0.22, 0.30, self.difficulty)

        if self.left_pressed:
            self.car_vx -= accel_now
        if self.right_pressed:
            self.car_vx += accel_now

        self.car_vx *= FRICTION
        self.car_vx = clamp(self.car_vx, -self.max_speed, self.max_speed)

        self.car_vy += GRAVITY
        self.car_x += self.car_vx
        self.car_y += self.car_vy

        if self.car_x < 120:
            self.car_x = 120
            self.car_vx = 0

        ground_y = get_ground_y(self.car_x)
        target_y = ground_y - 42
        slope = get_slope_angle(self.car_x)

        if self.car_y > target_y:
            impact_speed = self.car_vy
            self.car_y = target_y
            self.car_vy = -impact_speed * CAR_BOUNCE_DAMPING

            angle_diff = slope - self.car_angle
            self.car_angular_velocity += angle_diff * CAR_ANGLE_SPRING
            self.car_angular_velocity += self.car_vx * 0.0022
        else:
            self.car_angular_velocity += self.car_vx * CAR_AIR_ROTATION

        self.car_angular_velocity *= CAR_ANGULAR_DAMPING
        self.car_angle += self.car_angular_velocity

    def update_egg_in_basket(self):
        car_accel = self.car_vx - self.prev_car_vx
        sideways_gravity = math.sin(self.car_angle)

        slope_force = lerp(0.42, 0.62, self.difficulty)
        accel_force = lerp(0.26, 0.38, self.difficulty)

        roll_force = sideways_gravity * slope_force
        roll_force += (-car_accel) * accel_force

        if abs(self.car_vy) > 0.85 and self.car_y >= get_ground_y(self.car_x) - 42:
            roll_force += random.uniform(-0.15, 0.15)

        self.egg_roll_v += roll_force
        self.egg_roll_v *= EGG_ROLL_DAMPING
        self.egg_offset += self.egg_roll_v

        wall_limit = BASKET_HALF_WIDTH - 1.0
        hit_left = False
        hit_right = False

        if self.egg_offset < -wall_limit:
            self.egg_offset = -wall_limit
            hit_left = True
            if self.egg_roll_v < 0:
                self.egg_roll_v *= -EGG_WALL_BOUNCE

        if self.egg_offset > wall_limit:
            self.egg_offset = wall_limit
            hit_right = True
            if self.egg_roll_v > 0:
                self.egg_roll_v *= -EGG_WALL_BOUNCE

        if hit_left or hit_right:
            if abs(self.egg_roll_v) > 0.70:
                self.big_wobble_flash_timer = 10
            else:
                self.wobble_flash_timer = 7

        near_left_edge = self.egg_offset <= -(wall_limit - 0.8)
        near_right_edge = self.egg_offset >= (wall_limit - 0.8)

        if abs(self.car_angle) > TIP_FAIL_ANGLE:
            if (self.car_angle < 0 and near_right_edge) or (self.car_angle > 0 and near_left_edge):
                self.start_egg_fall()
                return

        if abs(self.car_vx) > self.max_speed * 0.92 and abs(self.car_angle) > math.radians(20):
            if hit_left or hit_right:
                self.start_egg_fall()
                return

    def get_egg_world_pos(self):
        base_x = self.car_x
        base_y = self.car_y - 28

        local_x = self.egg_offset
        local_y = -2

        cos_a = math.cos(self.car_angle)
        sin_a = math.sin(self.car_angle)

        world_x = base_x + local_x * cos_a - local_y * sin_a
        world_y = base_y + local_x * sin_a + local_y * cos_a
        return world_x, world_y

    def start_egg_fall(self):
        self.game_over = True
        self.egg_falling = True

        egg_world_x, egg_world_y = self.get_egg_world_pos()

        self.egg_x = egg_world_x
        self.egg_y = egg_world_y
        self.egg_vx = self.car_vx * 1.1 + math.sin(self.car_angle) * 2.4 + self.egg_roll_v * 0.9
        self.egg_vy = self.car_vy - 1.8

    def make_egg_particles(self):
        for _ in range(18):
            self.particles.append(Particle(self.egg_x, self.egg_y))

    def update(self):
        global camera_x

        if not self.game_over:
            self.prev_car_vx = self.car_vx

            self.update_car_physics()
            self.update_egg_in_basket()

            self.score = max(self.score, self.car_x - 180)
            self.best_distance = self.score

            if self.start_grace_timer > 0:
                self.start_grace_timer -= 1

            if self.car_x < 180 + self.start_grace_distance or self.start_grace_timer > 0:
                self.egg_roll_v *= 0.988

        else:
            if self.egg_falling:
                self.egg_vy += EGG_GRAVITY
                self.egg_x += self.egg_vx
                self.egg_y += self.egg_vy

                ground_y = get_ground_y(self.egg_x)
                if self.egg_y + 12 >= ground_y:
                    self.egg_y = ground_y - 12
                    self.egg_falling = False
                    self.egg_broken = True
                    self.make_egg_particles()

        if self.wobble_flash_timer > 0:
            self.wobble_flash_timer -= 1
        if self.big_wobble_flash_timer > 0:
            self.big_wobble_flash_timer -= 1

        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

        target_camera = self.car_x - 250
        camera_x += (target_camera - camera_x) * 0.08

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
        screen_x = self.car_x - camera_x
        body_y = self.car_y
        body_center = (screen_x, body_y)
    
        car_surface = pygame.Surface((170, 130), pygame.SRCALPHA)
        cx = 85
        cy = 68
    
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
    
        basket_y = cy - 34
        basket_left = cx - BASKET_HALF_WIDTH - 3
        basket_width = BASKET_HALF_WIDTH * 2 + 6
    
        left_wall_rect = pygame.Rect(
            basket_left,
            basket_y - BASKET_WALL_HEIGHT,
            5,
            BASKET_WALL_HEIGHT + 3
        )
        right_wall_rect = pygame.Rect(
            basket_left + basket_width - 5,
            basket_y - BASKET_WALL_HEIGHT,
            5,
            BASKET_WALL_HEIGHT + 3
        )
        floor_rect = pygame.Rect(
            basket_left,
            basket_y,
            basket_width,
            BASKET_FLOOR_THICKNESS
        )
    
        # back basket
        pygame.draw.rect(car_surface, BASKET, floor_rect, border_radius=4)
        pygame.draw.rect(car_surface, BASKET_DARK, floor_rect, 2, border_radius=4)
        pygame.draw.rect(car_surface, BASKET, left_wall_rect, border_radius=3)
        pygame.draw.rect(car_surface, BASKET, right_wall_rect, border_radius=3)
    
        # egg sits inside basket
        if not self.egg_broken and not self.egg_falling:
            egg_center_x = int(cx + self.egg_offset)
            egg_rect = pygame.Rect(0, 0, EGG_RADIUS_X * 2, EGG_RADIUS_Y * 2)
            egg_rect.center = (egg_center_x, basket_y - 5)
            pygame.draw.ellipse(car_surface, EGG, egg_rect)
            pygame.draw.ellipse(car_surface, EGG_LINE, egg_rect, 2)
    
        # front basket outlines/walls so they appear in front of egg
        pygame.draw.rect(car_surface, BASKET_DARK, left_wall_rect, 2, border_radius=3)
        pygame.draw.rect(car_surface, BASKET_DARK, right_wall_rect, 2, border_radius=3)
    
        front_lip_rect = pygame.Rect(
            basket_left,
            basket_y + 1,
            basket_width,
            BASKET_FLOOR_THICKNESS - 1
        )
        pygame.draw.rect(car_surface, BASKET, front_lip_rect, border_radius=4)
        pygame.draw.rect(car_surface, BASKET_DARK, front_lip_rect, 2, border_radius=4)
    
        rotated = pygame.transform.rotate(car_surface, -math.degrees(self.car_angle))
        rect = rotated.get_rect(center=(int(body_center[0]), int(body_center[1])))
        surface.blit(rotated, rect)
    
        if self.egg_falling and not self.egg_broken:
            egg_rect = pygame.Rect(0, 0, EGG_RADIUS_X * 2, EGG_RADIUS_Y * 2)
            egg_rect.center = (int(self.egg_x - camera_x), int(self.egg_y))
            pygame.draw.ellipse(surface, EGG, egg_rect)
            pygame.draw.ellipse(surface, EGG_LINE, egg_rect, 2)
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

        balance_ratio = 1.0 - min(1.0, abs(self.egg_offset) / BASKET_HALF_WIDTH)
        balance_percent = int(balance_ratio * 100)
        balance_text = SMALL_FONT.render(f"Egg Position: {balance_percent}%", True, BLACK)

        difficulty_percent = int(self.difficulty * 100)
        difficulty_text = SMALL_FONT.render(f"Difficulty: {difficulty_percent}%", True, BLACK)

        surface.blit(score_text, (25, 20))
        surface.blit(speed_text, (25, 60))
        surface.blit(balance_text, (25, 90))
        surface.blit(difficulty_text, (25, 185))

        pygame.draw.rect(surface, BLACK, (25, 125, 220, 24), 2)
        pygame.draw.rect(surface, BLUE, (27, 127, int(216 * balance_ratio), 20))

        pygame.draw.rect(surface, BLACK, (25, 215, 220, 18), 2)
        pygame.draw.rect(surface, ORANGE, (27, 217, int(216 * self.difficulty), 14))

        controls = SMALL_FONT.render("A/D or Arrow Keys to drive", True, BLACK)
        surface.blit(controls, (25, 245))

        if self.start_grace_timer > 0 or self.car_x < 180 + self.start_grace_distance:
            grace_text = SMALL_FONT.render("Easy start zone", True, BLACK)
            surface.blit(grace_text, (25, 275))

        if self.big_wobble_flash_timer > 0:
            wobble_text = SMALL_FONT.render("Huge bump!", True, DARK_RED)
            surface.blit(wobble_text, (25, 305))
        elif self.wobble_flash_timer > 0:
            wobble_text = SMALL_FONT.render("Basket hit!", True, DARK_RED)
            surface.blit(wobble_text, (25, 305))

    def draw_game_over(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        surface.blit(overlay, (0, 0))

        title = BIG_FONT.render("Game Over", True, WHITE)
        msg1 = FONT.render("The egg fell out of the basket.", True, WHITE)
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
    subtitle = FONT.render("Drive over hills without losing the egg.", True, BLACK)
    controls1 = SMALL_FONT.render("A / D or Left / Right Arrow Keys to move", True, BLACK)
    controls2 = SMALL_FONT.render("Press SPACE to start", True, BLACK)

    pygame.draw.circle(SCREEN, YELLOW, (930, 110), 55)

    pygame.draw.rect(SCREEN, RED, (455, 355, 150, 35), border_radius=10)
    pygame.draw.circle(SCREEN, BLACK, (490, 405), 18)
    pygame.draw.circle(SCREEN, BLACK, (570, 405), 18)
    pygame.draw.circle(SCREEN, LIGHT_GRAY, (490, 405), 8)
    pygame.draw.circle(SCREEN, LIGHT_GRAY, (570, 405), 8)

    pygame.draw.rect(SCREEN, BASKET, (514, 327, 32, 7), border_radius=4)
    pygame.draw.rect(SCREEN, BASKET, (514, 318, 5, 12), border_radius=3)
    pygame.draw.rect(SCREEN, BASKET, (541, 318, 5, 12), border_radius=3)
    pygame.draw.rect(SCREEN, BASKET_DARK, (514, 327, 32, 7), 2, border_radius=4)

    pygame.draw.ellipse(SCREEN, EGG, (522, 301, 16, 24))
    pygame.draw.ellipse(SCREEN, EGG_LINE, (522, 301, 16, 24), 2)

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