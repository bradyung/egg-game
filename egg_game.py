
import json
import math
import os
import random
import sys
import pygame

pygame.init()
try:
    pygame.mixer.init()
except pygame.error:
    pass

WIDTH = 1100
HEIGHT = 700
FPS = 60

SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Egg Balance Rover Deluxe")
CLOCK = pygame.time.Clock()

FONT = pygame.font.SysFont("arial", 28)
BIG_FONT = pygame.font.SysFont("arial", 54, bold=True)
MED_FONT = pygame.font.SysFont("arial", 36, bold=True)
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
EGG_SHELL = (245, 235, 210)
EGG_LINE = (140, 100, 70)
BLUE = (60, 90, 220)
BASKET = (160, 105, 60)
BASKET_DARK = (110, 70, 35)
ORANGE = (245, 150, 60)
PURPLE = (120, 80, 200)
GOLD = (235, 195, 70)
GRAY = (110, 110, 110)

GROUND_BASE = 520

CAR_WIDTH = 96
CAR_HEIGHT = 30
WHEEL_RADIUS = 16

CAR_RIDE_HEIGHT = 44
CAR_TO_BASKET_Y = 34
CAR_TO_EGG_BASE_Y = 28

FRICTION = 0.972
BASE_MAX_SPEED = 4.9
GRAVITY = 0.56
EGG_GRAVITY = 0.45

START_FLAT_DISTANCE = 760
TRANSITION_DISTANCE = 360

BASKET_HALF_WIDTH = 22
BASKET_WALL_HEIGHT = 10
BASKET_FLOOR_THICKNESS = 7
BASKET_WALL_WIDTH = 6
BASKET_PADDING = 1.0

EGG_RADIUS_X = 10
EGG_RADIUS_Y = 13
EGG_ROLL_DAMPING = 0.994
EGG_WALL_BOUNCE = 0.92
EGG_LOCAL_GRAVITY = 0.23
EGG_LOCAL_BOUNCE = 0.50
EGG_LOCAL_AIR_DAMPING = 0.995
EGG_FLOOR_FRICTION = 0.991

TIP_FAIL_ANGLE = math.radians(34)
ESCAPE_MARGIN = 1.0
ESCAPE_UPWARD_VELOCITY = 1.28

UPHILL_ASSIST = 0.08
UPHILL_DRAG_REDUCTION = 0.992

SAVE_FILE = "egg_rover_save.json"

camera_x = 0.0

EGG_SKINS = [
    {"name": "Classic Egg", "unlock": 0, "fill": (245, 235, 210), "line": (140, 100, 70)},
    {"name": "Blue Egg", "unlock": 250, "fill": (185, 220, 255), "line": (70, 110, 165)},
    {"name": "Striped Egg", "unlock": 900, "fill": (255, 245, 210), "line": (165, 90, 90)},
    {"name": "Gold Egg", "unlock": 2000, "fill": (245, 210, 90), "line": (155, 110, 35)},
]

CAR_SKINS = [
    {"name": "Red Rover", "unlock": 0, "body": RED, "trim": DARK_RED, "wheel": BLACK},
    {"name": "Blue Car", "unlock": 500, "body": (75, 115, 235), "trim": (35, 65, 150), "wheel": BLACK},
    {"name": "Truck Body", "unlock": 1400, "body": (90, 90, 100), "trim": (45, 45, 55), "wheel": BLACK},
]

CHECKPOINTS = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
AIRTIME_TIERS = [(0.30, 20), (0.80, 50), (1.20, 90)]


def clamp(value, low, high):
    return max(low, min(high, value))


def lerp(a, b, t):
    return a + (b - a) * t


def smoothstep(edge0, edge1, x):
    if edge1 == edge0:
        return 1.0
    t = clamp((x - edge0) / (edge1 - edge0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def get_difficulty_from_x(x):
    return clamp((x - 220.0) / 3500.0, 0.0, 1.0)


def get_ground_y(x):
    difficulty = get_difficulty_from_x(x)

    big_hills = lerp(15, 32, difficulty) * math.sin(x * 0.0075)
    mid_bumps = lerp(4, 15, difficulty) * math.sin(x * 0.018)
    small_bumps = lerp(1.0, 4.6, difficulty) * math.sin(x * 0.048)
    rhythm_sections = lerp(0, 12, difficulty) * (math.sin(x * 0.0044) ** 2) * math.sin(x * 0.013)
    contour_mix = lerp(0, 7.0, difficulty) * math.sin(x * 0.0027 + 1.3) * math.sin(x * 0.0105)

    # shaped jump zones for airtime
    jump_a = -14 * math.exp(-((x - 1150) / 115) ** 2) + 18 * math.exp(-((x - 1270) / 85) ** 2)
    jump_b = -18 * math.exp(-((x - 2350) / 110) ** 2) + 24 * math.exp(-((x - 2480) / 88) ** 2)
    jump_c = -20 * math.exp(-((x - 3350) / 120) ** 2) + 28 * math.exp(-((x - 3500) / 92) ** 2)

    terrain = GROUND_BASE + big_hills + mid_bumps + small_bumps + rhythm_sections + contour_mix
    terrain += jump_a + jump_b + jump_c

    blend = smoothstep(START_FLAT_DISTANCE, START_FLAT_DISTANCE + TRANSITION_DISTANCE, x)
    return lerp(GROUND_BASE, terrain, blend)


def get_slope_angle(x):
    left = get_ground_y(x - 5)
    right = get_ground_y(x + 5)
    raw_angle = math.atan2(right - left, 10)
    return clamp(raw_angle, -math.radians(24), math.radians(24))


class Particle:
    def __init__(self, x, y, color, vx=None, vy=None, life=None, radius=None):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2.5, 2.5) if vx is None else vx
        self.vy = random.uniform(-4.5, -1.0) if vy is None else vy
        self.life = random.randint(18, 35) if life is None else life
        self.radius = random.randint(2, 4) if radius is None else radius
        self.color = color

    def update(self):
        self.vy += 0.16
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, surface, cam_x):
        if self.life <= 0:
            return
        pygame.draw.circle(surface, self.color, (int(self.x - cam_x), int(self.y)), self.radius)


class Popup:
    def __init__(self, text, color=WHITE, life=120):
        self.text = text
        self.color = color
        self.life = life
        self.total = life

    def update(self):
        self.life -= 1

    def draw(self, surface, y):
        if self.life <= 0:
            return
        alpha_ratio = self.life / max(1, self.total)
        wobble = int((1.0 - alpha_ratio) * 8)
        text = MED_FONT.render(self.text, True, self.color)
        shadow = MED_FONT.render(self.text, True, BLACK)
        rect = text.get_rect(center=(WIDTH // 2, y - wobble))
        surface.blit(shadow, (rect.x + 2, rect.y + 2))
        surface.blit(text, rect)


def ensure_mixer():
    # safe if audio device is unavailable
    return pygame.mixer.get_init() is not None


class SoundBank:
    def __init__(self):
        self.enabled = ensure_mixer()
        self.cache = {}

    def tone(self, name, freq=440, ms=80, volume=0.18):
        if not self.enabled:
            return None
        if name in self.cache:
            return self.cache[name]
        sample_rate = 22050
        n_samples = int(sample_rate * ms / 1000)
        arr = bytearray()
        amplitude = int(32767 * volume)
        for i in range(n_samples):
            t = i / sample_rate
            value = int(amplitude * math.sin(2 * math.pi * freq * t))
            arr += int(value).to_bytes(2, "little", signed=True)
        snd = pygame.mixer.Sound(buffer=bytes(arr))
        self.cache[name] = snd
        return snd

    def play(self, name, freq=440, ms=80, volume=0.18):
        if not self.enabled:
            return
        snd = self.tone(name, freq=freq, ms=ms, volume=volume)
        if snd:
            snd.play()


class Game:
    def __init__(self):
        self.sounds = SoundBank()
        self.save = self.load_save()
        self.best_distance = float(self.save.get("best_distance", 0.0))
        self.total_distance = float(self.save.get("total_distance", 0.0))
        self.selected_egg = int(self.save.get("selected_egg", 0))
        self.selected_car = int(self.save.get("selected_car", 0))
        self.unlocked_eggs = set(self.save.get("unlocked_eggs", [0]))
        self.unlocked_cars = set(self.save.get("unlocked_cars", [0]))
        self.reset(full_run=True)

    def load_save(self):
        if os.path.exists(SAVE_FILE):
            try:
                with open(SAVE_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_game(self):
        data = {
            "best_distance": self.best_distance,
            "total_distance": self.total_distance,
            "selected_egg": self.selected_egg,
            "selected_car": self.selected_car,
            "unlocked_eggs": sorted(self.unlocked_eggs),
            "unlocked_cars": sorted(self.unlocked_cars),
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def reset(self, full_run=True):
        spawn_distance = 0.0 if full_run else getattr(self, "last_checkpoint_distance", 0.0)
        self.car_x = 180.0 + spawn_distance
        self.car_y = get_ground_y(self.car_x) - CAR_RIDE_HEIGHT
        self.car_vx = 0.0
        self.car_vy = 0.0
        self.prev_car_vx = 0.0

        self.car_angle = 0.0
        self.car_angular_velocity = 0.0
        self.body_bounce = 0.0
        self.front_susp = 0.0
        self.back_susp = 0.0

        self.left_pressed = False
        self.right_pressed = False

        self.egg_offset = 0.0
        self.egg_roll_v = 0.0
        self.egg_local_y = -EGG_RADIUS_Y + 2
        self.egg_local_vy = 0.0

        self.egg_falling = False
        self.egg_broken = False
        self.egg_x = 0.0
        self.egg_y = 0.0
        self.egg_vx = 0.0
        self.egg_vy = 0.0

        self.score = max(0.0, spawn_distance)
        self.run_start_score = self.score
        self.game_over = False
        self.particles = []
        self.popups = []
        self.camera_shake = 0.0
        self.camera_zoom = 1.0

        self.difficulty = 0.0
        self.max_speed = BASE_MAX_SPEED

        self.wobble_flash_timer = 0
        self.big_wobble_flash_timer = 0

        self.start_grace_distance = 300
        self.start_grace_timer = FPS * 3 if full_run else FPS

        self.airtime_frames = 0
        self.longest_airtime = 0.0
        self.last_airtime_bonus = 0
        self.just_landed_airtime = 0.0

        self.last_checkpoint_distance = spawn_distance
        self.revive_available = spawn_distance > 0
        self.checkpoint_flash = 0

        self.new_unlocks_this_run = set()

    def current_egg_skin(self):
        return EGG_SKINS[self.selected_egg]

    def current_car_skin(self):
        return CAR_SKINS[self.selected_car]

    def next_unlock_distance(self):
        targets = []
        for i, skin in enumerate(EGG_SKINS):
            if i not in self.unlocked_eggs:
                targets.append(skin["unlock"])
        for i, skin in enumerate(CAR_SKINS):
            if i not in self.unlocked_cars:
                targets.append(skin["unlock"])
        return min(targets) if targets else None

    def unlock_content(self):
        run_distance = int(self.score)
        for i, skin in enumerate(EGG_SKINS):
            if run_distance >= skin["unlock"] and i not in self.unlocked_eggs:
                self.unlocked_eggs.add(i)
                self.popups.append(Popup(f'New Egg Unlocked: {skin["name"]}!', YELLOW, 150))
                self.sounds.play(f"unlockegg{i}", 830, 130, 0.15)
        for i, skin in enumerate(CAR_SKINS):
            if run_distance >= skin["unlock"] and i not in self.unlocked_cars:
                self.unlocked_cars.add(i)
                self.popups.append(Popup(f'New Car Unlocked: {skin["name"]}!', ORANGE, 150))
                self.sounds.play(f"unlockcar{i}", 620, 150, 0.15)
        self.save_game()

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_a, pygame.K_LEFT):
                self.left_pressed = True
            if event.key in (pygame.K_d, pygame.K_RIGHT):
                self.right_pressed = True
            if event.key == pygame.K_r and self.game_over:
                self.reset(full_run=True)
            if event.key == pygame.K_c and self.game_over and self.revive_available:
                self.reset(full_run=False)

        if event.type == pygame.KEYUP:
            if event.key in (pygame.K_a, pygame.K_LEFT):
                self.left_pressed = False
            if event.key in (pygame.K_d, pygame.K_RIGHT):
                self.right_pressed = False

    def add_dust(self, intensity=1):
        wheel_y = self.car_y + 15
        for dx in (-25, 25):
            ground_y = get_ground_y(self.car_x + dx)
            for _ in range(intensity):
                self.particles.append(
                    Particle(
                        self.car_x + dx + random.uniform(-4, 4),
                        ground_y - 2,
                        (190, 155, 95),
                        vx=random.uniform(-1.4, 1.4) - self.car_vx * 0.08,
                        vy=random.uniform(-2.2, -0.6),
                        life=random.randint(12, 22),
                        radius=random.randint(2, 4),
                    )
                )

    def update_car_physics(self):
        self.difficulty = get_difficulty_from_x(self.car_x)
        self.max_speed = lerp(BASE_MAX_SPEED, 6.6, self.difficulty)
        accel_now = lerp(0.23, 0.31, self.difficulty)

        if self.left_pressed:
            self.car_vx -= accel_now
        if self.right_pressed:
            self.car_vx += accel_now

        slope = get_slope_angle(self.car_x)
        uphill_factor = abs(math.sin(slope))

        if self.right_pressed and slope > 0:
            self.car_vx += UPHILL_ASSIST * uphill_factor
        if self.left_pressed and slope < 0:
            self.car_vx -= UPHILL_ASSIST * uphill_factor

        if (self.right_pressed and slope > 0) or (self.left_pressed and slope < 0):
            self.car_vx *= UPHILL_DRAG_REDUCTION
        else:
            self.car_vx *= FRICTION

        self.car_vx = clamp(self.car_vx, -self.max_speed, self.max_speed)

        self.car_vy += GRAVITY
        self.car_x += self.car_vx
        self.car_y += self.car_vy

        if self.car_x < 120:
            self.car_x = 120
            self.car_vx = 0

        ground_y = get_ground_y(self.car_x)
        target_y = ground_y - CAR_RIDE_HEIGHT
        front_ground = get_ground_y(self.car_x + 30)
        back_ground = get_ground_y(self.car_x - 30)

        on_ground = False
        landing_impact = 0.0

        if self.car_y > target_y:
            on_ground = True
            landing_impact = self.car_vy
            self.car_y = target_y
            self.car_vy = -landing_impact * 0.24
            self.body_bounce += min(7.5, abs(landing_impact) * 0.9)
            self.front_susp += min(10.0, max(0.0, (front_ground - ground_y) * 0.2 + abs(landing_impact) * 0.18))
            self.back_susp += min(10.0, max(0.0, (back_ground - ground_y) * 0.2 + abs(landing_impact) * 0.18))
            if abs(landing_impact) > 2.2:
                self.camera_shake = max(self.camera_shake, min(12.0, abs(landing_impact) * 1.8))
                self.add_dust(4)
                self.sounds.play("landheavy", 150, 90, 0.16)
            elif abs(landing_impact) > 1.0:
                self.add_dust(2)
                self.sounds.play("landlight", 210, 70, 0.12)

        slope = get_slope_angle(self.car_x)

        if on_ground:
            angle_diff = slope - self.car_angle
            self.car_angular_velocity += angle_diff * 0.11
            self.car_angular_velocity += self.car_vx * 0.0011
            self.car_angle = lerp(self.car_angle, slope, 0.075)
        else:
            self.car_angular_velocity += self.car_vx * 0.00085

        self.car_angular_velocity *= 0.89
        self.car_angle += self.car_angular_velocity
        self.car_angle = clamp(self.car_angle, -math.radians(40), math.radians(40))

        self.body_bounce *= 0.76
        self.front_susp = self.front_susp * 0.78 + (front_ground - ground_y) * 0.04
        self.back_susp = self.back_susp * 0.78 + (back_ground - ground_y) * 0.04

        return on_ground, landing_impact

    def update_egg_in_basket(self, on_ground, landing_impact):
        car_accel = self.car_vx - self.prev_car_vx
        sideways_gravity = math.sin(self.car_angle)

        slope_force = lerp(0.42, 0.63, self.difficulty)
        accel_force = lerp(0.26, 0.38, self.difficulty)

        roll_force = sideways_gravity * slope_force
        roll_force += (-car_accel) * accel_force

        if not on_ground:
            roll_force += math.sin(self.car_angle) * 0.10
            self.egg_local_vy -= self.car_angular_velocity * 2.2

        if on_ground and abs(landing_impact) > 0.7:
            roll_force += random.uniform(-0.18, 0.18) * clamp(abs(landing_impact) / 5.0, 0.0, 1.0)

        self.egg_roll_v += roll_force
        self.egg_roll_v *= EGG_ROLL_DAMPING
        self.egg_offset += self.egg_roll_v

        impact_push = -landing_impact * 0.38 if on_ground else 0.0
        self.egg_local_vy += EGG_LOCAL_GRAVITY + impact_push
        self.egg_local_y += self.egg_local_vy

        basket_floor_y = -EGG_RADIUS_Y + 2
        basket_ceiling_y = basket_floor_y - 20

        if self.egg_local_y > basket_floor_y:
            self.egg_local_y = basket_floor_y
            if self.egg_local_vy > 0:
                self.egg_local_vy *= -EGG_LOCAL_BOUNCE
            self.egg_roll_v *= EGG_FLOOR_FRICTION

        if self.egg_local_y < basket_ceiling_y:
            self.egg_local_y = basket_ceiling_y
            if self.egg_local_vy < 0:
                self.egg_local_vy *= -0.30

        self.egg_local_vy *= EGG_LOCAL_AIR_DAMPING

        wall_limit = BASKET_HALF_WIDTH - EGG_RADIUS_X - BASKET_PADDING
        hit_wall = False
        hit_strength = 0.0

        if self.egg_offset < -wall_limit:
            self.egg_offset = -wall_limit
            if self.egg_roll_v < 0:
                self.egg_roll_v *= -EGG_WALL_BOUNCE
                hit_wall = True
                hit_strength = abs(self.egg_roll_v)

        if self.egg_offset > wall_limit:
            self.egg_offset = wall_limit
            if self.egg_roll_v > 0:
                self.egg_roll_v *= -EGG_WALL_BOUNCE
                hit_wall = True
                hit_strength = abs(self.egg_roll_v)

        if hit_wall:
            self.egg_local_vy -= min(1.15, hit_strength * 0.25)
            self.sounds.play("wobble_big" if hit_strength > 1.0 else "wobble", 360 if hit_strength > 1.0 else 280, 50, 0.10)
            if hit_strength > 1.0:
                self.big_wobble_flash_timer = 10
            else:
                self.wobble_flash_timer = 7

        near_left_edge = self.egg_offset <= -(wall_limit - ESCAPE_MARGIN)
        near_right_edge = self.egg_offset >= (wall_limit - ESCAPE_MARGIN)
        egg_is_high = self.egg_local_y < basket_floor_y - BASKET_WALL_HEIGHT + 4
        egg_is_bouncing_up = self.egg_local_vy < -ESCAPE_UPWARD_VELOCITY

        tipped_right = self.car_angle > TIP_FAIL_ANGLE
        tipped_left = self.car_angle < -TIP_FAIL_ANGLE

        if tipped_right and near_right_edge and (egg_is_high or egg_is_bouncing_up):
            self.start_egg_fall()
            return
        if tipped_left and near_left_edge and (egg_is_high or egg_is_bouncing_up):
            self.start_egg_fall()
            return

        if abs(self.car_vx) > self.max_speed * 0.98 and abs(self.car_angle) > math.radians(28):
            if hit_wall and egg_is_high:
                self.start_egg_fall()

    def get_egg_world_pos(self):
        base_x = self.car_x
        base_y = self.car_y - CAR_TO_EGG_BASE_Y - self.body_bounce * 0.2

        local_x = self.egg_offset
        local_y = self.egg_local_y

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
        self.egg_vx = self.car_vx * 1.06 + math.sin(self.car_angle) * 2.0 + self.egg_roll_v * 0.95
        self.egg_vy = self.car_vy + self.egg_local_vy - 1.1
        self.camera_shake = max(self.camera_shake, 10.0)
        self.sounds.play("crack_start", 180, 120, 0.18)

    def make_egg_particles(self):
        shell_color = self.current_egg_skin()["fill"]
        for _ in range(18):
            self.particles.append(
                Particle(
                    self.egg_x,
                    self.egg_y,
                    shell_color,
                    vx=random.uniform(-3.5, 3.5),
                    vy=random.uniform(-6.2, -2.4),
                    life=random.randint(25, 45),
                    radius=random.randint(2, 5),
                )
            )
        for _ in range(8):
            self.particles.append(
                Particle(
                    self.egg_x,
                    self.egg_y + 4,
                    YELLOW,
                    vx=random.uniform(-2.0, 2.0),
                    vy=random.uniform(-2.5, -0.8),
                    life=random.randint(16, 28),
                    radius=random.randint(3, 5),
                )
            )

    def update_checkpoints(self):
        for cp in CHECKPOINTS:
            if self.score >= cp and self.last_checkpoint_distance < cp:
                self.last_checkpoint_distance = cp
                self.revive_available = True
                self.checkpoint_flash = 90
                self.popups.append(Popup(f"Checkpoint! {cp} m", BLUE, 100))
                self.sounds.play(f"checkpoint{cp}", 520, 140, 0.16)
                return

    def update_airtime(self, on_ground):
        if on_ground:
            if self.airtime_frames > 0:
                airtime = self.airtime_frames / FPS
                self.longest_airtime = max(self.longest_airtime, airtime)
                self.just_landed_airtime = airtime
                bonus = 0
                for need, pts in AIRTIME_TIERS:
                    if airtime >= need:
                        bonus = pts
                if bonus > 0:
                    self.last_airtime_bonus = bonus
                    self.popups.append(Popup(f"Airtime +{bonus}", PURPLE, 90))
                    self.sounds.play("airtime", 700, 80, 0.13)
                self.airtime_frames = 0
        else:
            self.airtime_frames += 1

    def update(self):
        global camera_x
        if not self.game_over:
            self.prev_car_vx = self.car_vx
            on_ground, landing_impact = self.update_car_physics()
            self.update_airtime(on_ground)
            self.update_egg_in_basket(on_ground, landing_impact)

            if on_ground and abs(self.car_vx) > 1.8 and (self.left_pressed or self.right_pressed):
                self.add_dust(1)

            self.score = max(self.score, self.car_x - 180)
            self.best_distance = max(self.best_distance, self.score)

            if self.start_grace_timer > 0:
                self.start_grace_timer -= 1

            if self.car_x < 180 + self.start_grace_distance or self.start_grace_timer > 0:
                self.egg_roll_v *= 0.989

            self.update_checkpoints()
            self.unlock_content()

        else:
            if self.egg_falling:
                self.egg_vy += EGG_GRAVITY
                self.egg_x += self.egg_vx
                self.egg_y += self.egg_vy
                ground_y = get_ground_y(self.egg_x)
                if self.egg_y + EGG_RADIUS_Y >= ground_y:
                    self.egg_y = ground_y - EGG_RADIUS_Y
                    self.egg_falling = False
                    self.egg_broken = True
                    self.make_egg_particles()
                    self.sounds.play("crack_end", 120, 180, 0.20)

        if self.wobble_flash_timer > 0:
            self.wobble_flash_timer -= 1
        if self.big_wobble_flash_timer > 0:
            self.big_wobble_flash_timer -= 1
        if self.checkpoint_flash > 0:
            self.checkpoint_flash -= 1
        self.camera_shake *= 0.85

        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

        for popup in self.popups[:]:
            popup.update()
            if popup.life <= 0:
                self.popups.remove(popup)

        speed_ratio = min(1.0, abs(self.car_vx) / max(0.01, self.max_speed))
        look_ahead = self.car_vx * 38
        target_camera = self.car_x - 260 + look_ahead
        shake = random.uniform(-self.camera_shake, self.camera_shake)
        camera_x += (target_camera - camera_x) * 0.08
        camera_x += shake
        self.camera_zoom = 1.0 - speed_ratio * 0.035

        # career distance only updates on best progress in current run
        self.total_distance = max(self.total_distance, self.score)
        self.save_game()

    def draw_background(self, surface):
        surface.fill(SKY)
        pygame.draw.circle(surface, YELLOW, (930, 110), 55)

        for i in range(4):
            x = (i * 320) - (camera_x * 0.12 % 320)
            pygame.draw.ellipse(surface, (205, 225, 245), (x, 265, 320, 140))
        for i in range(5):
            x = (i * 260) - (camera_x * 0.28 % 260)
            pygame.draw.polygon(surface, (118, 165, 130), [(x, 460), (x + 80, 360), (x + 160, 460)])
        for i in range(7):
            x = (i * 190) - (camera_x * 0.46 % 190)
            pygame.draw.polygon(surface, (90, 145, 88), [(x, 480), (x + 38, 425), (x + 76, 480)])

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

        for cp in CHECKPOINTS:
            world_x = cp + 180
            if camera_x - 60 <= world_x <= camera_x + WIDTH + 60:
                sx = world_x - camera_x
                gy = get_ground_y(world_x)
                pole_h = 70 if self.last_checkpoint_distance < cp else 84
                pygame.draw.rect(surface, (90, 90, 90), (sx - 2, gy - pole_h, 4, pole_h))
                flag_color = BLUE if self.last_checkpoint_distance >= cp else WHITE
                pygame.draw.polygon(surface, flag_color, [(sx + 2, gy - pole_h), (sx + 34, gy - pole_h + 12), (sx + 2, gy - pole_h + 22)])
                if self.last_checkpoint_distance >= cp:
                    pygame.draw.circle(surface, YELLOW, (int(sx + 12), int(gy - pole_h + 12)), 4)

    def draw_car(self, surface):
        screen_x = self.car_x - camera_x
        body_y = self.car_y - self.body_bounce * 0.26
        car_surface = pygame.Surface((190, 145), pygame.SRCALPHA)
        cx = 95
        cy = 76

        car_skin = self.current_car_skin()
        egg_skin = self.current_egg_skin()

        body_rect = pygame.Rect(cx - CAR_WIDTH // 2, cy - CAR_HEIGHT // 2, CAR_WIDTH, CAR_HEIGHT)
        top_rect = pygame.Rect(cx - 22, cy - 30, 48, 20)
        body_color = car_skin["body"]
        trim_color = car_skin["trim"]

        left_wheel_y = cy + 17 + int(self.back_susp * 0.35)
        right_wheel_y = cy + 17 + int(self.front_susp * 0.35)

        for x, y in ((cx - 25, left_wheel_y), (cx + 25, right_wheel_y)):
            pygame.draw.line(car_surface, (80, 80, 80), (x, cy + 7), (x, y - 5), 4)

        pygame.draw.rect(car_surface, body_color, body_rect, border_radius=9)
        pygame.draw.rect(car_surface, trim_color, body_rect, 3, border_radius=9)
        pygame.draw.rect(car_surface, body_color, top_rect, border_radius=7)
        pygame.draw.rect(car_surface, trim_color, top_rect, 3, border_radius=7)

        for wheel in ((cx - 25, left_wheel_y), (cx + 25, right_wheel_y)):
            pygame.draw.circle(car_surface, car_skin["wheel"], wheel, WHEEL_RADIUS)
            pygame.draw.circle(car_surface, LIGHT_GRAY, wheel, 7)

        basket_y = cy - CAR_TO_BASKET_Y
        basket_left = cx - BASKET_HALF_WIDTH - 4
        basket_width = BASKET_HALF_WIDTH * 2 + 8

        floor_rect = pygame.Rect(basket_left, basket_y, basket_width, BASKET_FLOOR_THICKNESS)
        left_wall_rect = pygame.Rect(basket_left, basket_y - BASKET_WALL_HEIGHT, BASKET_WALL_WIDTH, BASKET_WALL_HEIGHT + 3)
        right_wall_rect = pygame.Rect(basket_left + basket_width - BASKET_WALL_WIDTH, basket_y - BASKET_WALL_HEIGHT, BASKET_WALL_WIDTH, BASKET_WALL_HEIGHT + 3)
        left_curve_rect = pygame.Rect(basket_left - 2, basket_y - BASKET_WALL_HEIGHT + 1, BASKET_WALL_WIDTH + 5, BASKET_WALL_HEIGHT + 1)
        right_curve_rect = pygame.Rect(basket_left + basket_width - BASKET_WALL_WIDTH - 3, basket_y - BASKET_WALL_HEIGHT + 1, BASKET_WALL_WIDTH + 5, BASKET_WALL_HEIGHT + 1)

        pygame.draw.rect(car_surface, BASKET, floor_rect, border_radius=4)
        pygame.draw.rect(car_surface, BASKET_DARK, floor_rect, 2, border_radius=4)
        pygame.draw.rect(car_surface, BASKET, left_wall_rect, border_radius=4)
        pygame.draw.rect(car_surface, BASKET, right_wall_rect, border_radius=4)
        pygame.draw.arc(car_surface, BASKET, left_curve_rect, math.radians(80), math.radians(185), 5)
        pygame.draw.arc(car_surface, BASKET, right_curve_rect, math.radians(-5), math.radians(100), 5)

        lip_rect = pygame.Rect(basket_left + 6, basket_y + 1, basket_width - 12, 4)
        pygame.draw.rect(car_surface, (178, 120, 70), lip_rect, border_radius=3)

        if not self.egg_broken and not self.egg_falling:
            egg_center_x = int(cx + self.egg_offset)
            egg_center_y = int(basket_y + self.egg_local_y)
            egg_rect = pygame.Rect(0, 0, EGG_RADIUS_X * 2, EGG_RADIUS_Y * 2)
            egg_rect.center = (egg_center_x, egg_center_y)
            pygame.draw.ellipse(car_surface, egg_skin["fill"], egg_rect)
            pygame.draw.ellipse(car_surface, egg_skin["line"], egg_rect, 2)
            if self.selected_egg == 2:
                for stripe_y in (-5, 0, 5):
                    pygame.draw.line(car_surface, (200, 110, 110), (egg_center_x - 5, egg_center_y + stripe_y), (egg_center_x + 5, egg_center_y + stripe_y - 1), 2)

        pygame.draw.rect(car_surface, BASKET_DARK, left_wall_rect, 2, border_radius=3)
        pygame.draw.rect(car_surface, BASKET_DARK, right_wall_rect, 2, border_radius=3)

        rotated = pygame.transform.rotate(car_surface, -math.degrees(self.car_angle))
        rect = rotated.get_rect(center=(int(screen_x), int(body_y)))
        surface.blit(rotated, rect)

        if self.egg_falling and not self.egg_broken:
            egg_rect = pygame.Rect(0, 0, EGG_RADIUS_X * 2, EGG_RADIUS_Y * 2)
            egg_rect.center = (int(self.egg_x - camera_x), int(self.egg_y))
            pygame.draw.ellipse(surface, egg_skin["fill"], egg_rect)
            pygame.draw.ellipse(surface, egg_skin["line"], egg_rect, 2)

    def draw_broken_egg(self, surface):
        if not self.egg_broken:
            return
        sx = int(self.egg_x - camera_x)
        sy = int(self.egg_y)
        shell_color = self.current_egg_skin()["fill"]
        pygame.draw.ellipse(surface, YELLOW, (sx - 12, sy - 4, 24, 12))
        left_shell = [(sx - 20, sy + 2), (sx - 8, sy - 10), (sx - 2, sy + 5)]
        right_shell = [(sx + 20, sy + 2), (sx + 8, sy - 10), (sx + 2, sy + 5)]
        pygame.draw.polygon(surface, shell_color, left_shell)
        pygame.draw.polygon(surface, shell_color, right_shell)
        pygame.draw.polygon(surface, EGG_LINE, left_shell, 2)
        pygame.draw.polygon(surface, EGG_LINE, right_shell, 2)

    def draw_particles(self, surface):
        for p in self.particles:
            p.draw(surface, camera_x)

    def draw_hud(self, surface):
        wall_limit = BASKET_HALF_WIDTH - EGG_RADIUS_X - BASKET_PADDING
        balance_ratio = 1.0 - min(1.0, abs(self.egg_offset) / max(1.0, wall_limit))
        difficulty_percent = int(self.difficulty * 100)

        # top HUD background bar
        hud_height = 110
        hud = pygame.Surface((WIDTH, hud_height), pygame.SRCALPHA)
        hud.fill((255, 255, 255, 170))
        surface.blit(hud, (0, 0))
        pygame.draw.line(surface, (60, 60, 60), (0, hud_height), (WIDTH, hud_height), 2)

        # left info
        surface.blit(FONT.render(f"Distance: {int(self.score)}", True, BLACK), (20, 10))
        surface.blit(SMALL_FONT.render(f"Best: {int(self.best_distance)}", True, BLACK), (20, 42))
        surface.blit(SMALL_FONT.render(f"Speed: {self.car_vx:.1f}", True, BLACK), (20, 70))

        # middle info
        surface.blit(SMALL_FONT.render(f"Checkpoint: {int(self.last_checkpoint_distance)}", True, BLACK), (220, 14))
        surface.blit(SMALL_FONT.render(f"", True, BLACK), (220, 42))
        surface.blit(SMALL_FONT.render(f"Difficulty: {difficulty_percent}%", True, BLACK), (220, 70))

        # egg balance bar
        bar_x = 430
        bar_y = 18
        bar_w = 180
        bar_h = 16
        pygame.draw.rect(surface, BLACK, (bar_x, bar_y, bar_w, bar_h), 2)
        pygame.draw.rect(surface, BLUE, (bar_x + 2, bar_y + 2, int((bar_w - 4) * balance_ratio), bar_h - 4))
        surface.blit(SMALL_FONT.render("Egg Balance", True, BLACK), (430, 40))

        # next unlock
        next_unlock = self.next_unlock_distance()
        if next_unlock is not None:
            unlock_progress = clamp(self.score / next_unlock, 0.0, 1.0)
            unlock_x = 430
            unlock_y = 68
            unlock_w = 180
            unlock_h = 16
            pygame.draw.rect(surface, BLACK, (unlock_x, unlock_y, unlock_w, unlock_h), 2)
            pygame.draw.rect(surface, PURPLE, (unlock_x + 2, unlock_y + 2, int((unlock_w - 4) * unlock_progress), unlock_h - 4))
            surface.blit(SMALL_FONT.render(f"Next unlock: {next_unlock} m", True, BLACK), (620, 66))
        else:
            surface.blit(SMALL_FONT.render("", True, BLACK), (620, 88))

        # right side info
        skin_text = SMALL_FONT.render(
            f"Egg: {self.current_egg_skin()['name']} | Car: {self.current_car_skin()['name']}",
            True,
            BLACK,
        )
        controls = SMALL_FONT.render("Drive: A/D or Arrows", True, BLACK)
        restart = SMALL_FONT.render("R restart | C checkpoint", True, BLACK)

        surface.blit(skin_text, (700, 12))
        surface.blit(controls, (700, 42))
        surface.blit(restart, (700, 70))

        if self.start_grace_timer > 0 or self.car_x < 180 + self.start_grace_distance:
            surface.blit(SMALL_FONT.render("", True, DARK_GREEN), (930, 12))

        if self.big_wobble_flash_timer > 0:
            surface.blit(SMALL_FONT.render("Huge bump!", True, DARK_RED), (930, 42))
        elif self.wobble_flash_timer > 0:
            surface.blit(SMALL_FONT.render("Basket hit!", True, DARK_RED), (930, 42))

        
    def draw_popups(self, surface):
        y = 125
        for popup in self.popups[:3]:
            popup.draw(surface, y)
            y += 50

    def draw_game_over(self, surface):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 130))
        surface.blit(overlay, (0, 0))

        title = BIG_FONT.render("Game Over", True, WHITE)
        msg1 = FONT.render("The egg fell out of the basket.", True, WHITE)
        msg2 = FONT.render(f"Distance: {int(self.score)}", True, WHITE)
        msg3 = SMALL_FONT.render("Press R for a new run", True, WHITE)
        if self.revive_available:
            msg4 = SMALL_FONT.render(
                f"Press C to continue from {int(self.last_checkpoint_distance)} m",
                True,
                WHITE,
            )
        else:
            msg4 = SMALL_FONT.render("No checkpoint continue yet", True, WHITE)

        surface.blit(title, title.get_rect(center=(WIDTH // 2, 230)))
        surface.blit(msg1, msg1.get_rect(center=(WIDTH // 2, 300)))
        surface.blit(msg2, msg2.get_rect(center=(WIDTH // 2, 346)))
        surface.blit(msg3, msg3.get_rect(center=(WIDTH // 2, 400)))
        surface.blit(msg4, msg4.get_rect(center=(WIDTH // 2, 435)))

    def draw(self, surface):
        self.draw_background(surface)
        self.draw_ground(surface)
        self.draw_car(surface)
        self.draw_broken_egg(surface)
        self.draw_particles(surface)
        self.draw_hud(surface)
        self.draw_popups(surface)
        if self.game_over:
            self.draw_game_over(surface)


def draw_start_screen():
    SCREEN.fill(SKY)
    title = BIG_FONT.render("Egg Balance Rover Deluxe", True, BLACK)
    subtitle = FONT.render("Drive the hills. Protect the egg. Unlock new skins.", True, BLACK)
    controls1 = SMALL_FONT.render("SPACE = Play | G = Garage", True, BLACK)
    controls2 = SMALL_FONT.render("A / D or Left / Right Arrow Keys to drive", True, BLACK)

    pygame.draw.circle(SCREEN, YELLOW, (930, 110), 55)
    pygame.draw.rect(SCREEN, RED, (445, 355, 165, 35), border_radius=10)
    pygame.draw.circle(SCREEN, BLACK, (485, 405), 18)
    pygame.draw.circle(SCREEN, BLACK, (575, 405), 18)
    pygame.draw.circle(SCREEN, LIGHT_GRAY, (485, 405), 8)
    pygame.draw.circle(SCREEN, LIGHT_GRAY, (575, 405), 8)
    pygame.draw.rect(SCREEN, BASKET, (512, 327, 40, 7), border_radius=4)
    pygame.draw.rect(SCREEN, BASKET, (512, 316, 6, 14), border_radius=3)
    pygame.draw.rect(SCREEN, BASKET, (546, 316, 6, 14), border_radius=3)
    pygame.draw.ellipse(SCREEN, EGG_SHELL, (523, 301, 18, 24))
    pygame.draw.ellipse(SCREEN, EGG_LINE, (523, 301, 18, 24), 2)

    SCREEN.blit(title, title.get_rect(center=(WIDTH // 2, 140)))
    SCREEN.blit(subtitle, subtitle.get_rect(center=(WIDTH // 2, 210)))
    SCREEN.blit(controls1, controls1.get_rect(center=(WIDTH // 2, 520)))
    SCREEN.blit(controls2, controls2.get_rect(center=(WIDTH // 2, 560)))


def draw_garage(game, selected_section):
    SCREEN.fill((210, 225, 245))
    title = BIG_FONT.render("Garage", True, BLACK)
    hint = SMALL_FONT.render("Left/Right changes selection, Up/Down switches row, Enter equips, Esc returns", True, BLACK)
    SCREEN.blit(title, title.get_rect(center=(WIDTH // 2, 70)))
    SCREEN.blit(hint, hint.get_rect(center=(WIDTH // 2, 115)))

    egg_title = MED_FONT.render("Egg Skins", True, BLACK)
    car_title = MED_FONT.render("Car Skins", True, BLACK)
    SCREEN.blit(egg_title, (120, 170))
    SCREEN.blit(car_title, (120, 390))

    egg_index = game.selected_egg
    car_index = game.selected_car

    for i, skin in enumerate(EGG_SKINS):
        x = 120 + i * 220
        y = 220
        box = pygame.Rect(x, y, 180, 110)
        is_selected = selected_section == "egg" and i == egg_index
        is_unlocked = i in game.unlocked_eggs
        pygame.draw.rect(SCREEN, WHITE if is_selected else (240, 240, 240), box, border_radius=12)
        pygame.draw.rect(SCREEN, BLUE if is_selected else BLACK, box, 3, border_radius=12)
        egg_rect = pygame.Rect(x + 72, y + 18, 36, 52)
        fill = skin["fill"] if is_unlocked else (160, 160, 160)
        pygame.draw.ellipse(SCREEN, fill, egg_rect)
        pygame.draw.ellipse(SCREEN, skin["line"], egg_rect, 2)
        name = SMALL_FONT.render(skin["name"], True, BLACK)
        status = SMALL_FONT.render("Unlocked" if is_unlocked else f'{skin["unlock"]} m', True, BLACK)
        SCREEN.blit(name, (x + 18, y + 76))
        SCREEN.blit(status, (x + 18, y + 98))

    for i, skin in enumerate(CAR_SKINS):
        x = 120 + i * 220
        y = 440
        box = pygame.Rect(x, y, 180, 110)
        is_selected = selected_section == "car" and i == car_index
        is_unlocked = i in game.unlocked_cars
        pygame.draw.rect(SCREEN, WHITE if is_selected else (240, 240, 240), box, border_radius=12)
        pygame.draw.rect(SCREEN, ORANGE if is_selected else BLACK, box, 3, border_radius=12)
        color = skin["body"] if is_unlocked else (160, 160, 160)
        trim = skin["trim"] if is_unlocked else (105, 105, 105)
        pygame.draw.rect(SCREEN, color, (x + 46, y + 34, 90, 22), border_radius=8)
        pygame.draw.rect(SCREEN, trim, (x + 46, y + 34, 90, 22), 3, border_radius=8)
        pygame.draw.circle(SCREEN, BLACK, (x + 65, y + 63), 13)
        pygame.draw.circle(SCREEN, BLACK, (x + 118, y + 63), 13)
        name = SMALL_FONT.render(skin["name"], True, BLACK)
        status = SMALL_FONT.render("Unlocked" if is_unlocked else f'{skin["unlock"]} m', True, BLACK)
        SCREEN.blit(name, (x + 18, y + 76))
        SCREEN.blit(status, (x + 18, y + 98))


def main():
    global camera_x
    game = Game()
    state = "start"
    garage_section = "egg"

    while True:
        CLOCK.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if state == "start":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        game.reset(full_run=True)
                        camera_x = 0
                        state = "play"
                    elif event.key == pygame.K_g:
                        state = "garage"
            elif state == "garage":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        state = "start"
                    elif event.key in (pygame.K_UP, pygame.K_DOWN):
                        garage_section = "car" if garage_section == "egg" else "egg"
                    elif event.key == pygame.K_LEFT:
                        if garage_section == "egg":
                            game.selected_egg = max(0, game.selected_egg - 1)
                        else:
                            game.selected_car = max(0, game.selected_car - 1)
                    elif event.key == pygame.K_RIGHT:
                        if garage_section == "egg":
                            game.selected_egg = min(len(EGG_SKINS) - 1, game.selected_egg + 1)
                        else:
                            game.selected_car = min(len(CAR_SKINS) - 1, game.selected_car + 1)
                    elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        if garage_section == "egg" and game.selected_egg not in game.unlocked_eggs:
                            locked = [i for i in sorted(game.unlocked_eggs)]
                            game.selected_egg = locked[-1]
                        if garage_section == "car" and game.selected_car not in game.unlocked_cars:
                            locked = [i for i in sorted(game.unlocked_cars)]
                            game.selected_car = locked[-1]
                        game.save_game()
            else:
                game.handle_event(event)

        if state == "start":
            draw_start_screen()
        elif state == "garage":
            draw_garage(game, garage_section)
        else:
            game.update()
            game.draw(SCREEN)

        pygame.display.flip()


if __name__ == "__main__":
    main()