import pygame
import random
import math


def line_circle_intersection(p1, p2, circle_center, radius):
    """Проверка пересечения отрезка ножа (p1->p2) с кругом фрукта"""
    px, py = p1
    dx = p2[0] - px
    dy = p2[1] - py
    if dx == 0 and dy == 0:
        return math.hypot(px - circle_center[0], py - circle_center[1]) <= radius

    t = ((circle_center[0] - px) * dx + (circle_center[1] - py) * dy) / (dx * dx + dy * dy)
    t = max(0.0, min(1.0, t))

    nearest_x = px + t * dx
    nearest_y = py + t * dy
    dist = math.hypot(nearest_x - circle_center[0], nearest_y - circle_center[1])
    return dist <= radius


class Fruit:
    def __init__(self, window_w, window_h, scale, assets):
        self.window_w = window_w
        self.window_h = window_h
        self.scale = scale
        self.assets = assets

        fruit_types = [
            ("apple", "apple.png", "apple_half_1.png", "apple_half_2.png"),
            ("banana", "banana.png", "banana_half_1.png", "banana_half_2.png"),
            ("coconut", "coconut.png", "coconut_half_1.png", "coconut_half_2.png"),
            ("bomb", "bomb.png", None, None)
        ]

        weights = [0.28, 0.28, 0.28, 0.16]
        choice = random.choices(fruit_types, weights=weights)[0]

        self.type = choice[0]
        self.image_name = choice[1]
        self.half1_name = choice[2]
        self.half2_name = choice[3]

        self.original_image = assets.get(self.image_name)
        # Радиус коллизии под увеличенный размер фрукта
        self.radius = int(55 * scale)

        # self.x = random.randint(int(120 * scale), window_w - int(120 * scale))
        margin = int(window_w * 0.25)
        self.x = random.randint(margin, window_w - margin)

        # ЛИНИЯ СТОЛА: фрукты вылетают чуть выше нижней границы экрана (где рука еще видна камере)
        self.table_y = window_h - int(90 * scale)
        self.y = self.table_y

        # ДИНАМИЧЕСКИЙ РАСЧЕТ ВЫСОТЫ: подбрасываем фрукт до ~75% высоты экрана
        self.gravity = 0.45 * scale
        target_height = window_h * random.uniform(0.65, 0.80)  # Высота полета
        self.vy = -math.sqrt(2 * self.gravity * target_height)  # Скорость вылета по формуле физики
        self.vx = random.uniform(-3.0, 3.0) * scale

        self.angle = 0
        self.rot_speed = random.uniform(-4, 4)
        self.sliced = False

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.angle += self.rot_speed

    def draw(self, surface):
        if not self.original_image:
            return

        # Поворот картинки
        rotated_img = pygame.transform.rotate(self.original_image, self.angle)
        rect = rotated_img.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rotated_img, rect.topleft)

    def is_out_of_bounds(self):
        # Фрукт упал ниже экрана
        return self.y > self.window_h + int(100 * self.scale) and self.vy > 0


class FruitHalf:
    """Половинка фрукта после разреза"""

    def __init__(self, x, y, image, is_left, scale):
        self.x = x
        self.y = y
        self.scale = scale
        self.original_image = image

        # Расталкивание половинок в разные стороны
        push = random.uniform(3.0, 6.0) * scale
        self.vx = -push if is_left else push
        self.vy = random.uniform(-4.0, -1.0) * scale
        self.gravity = 0.5 * (scale ** 0.5)

        self.angle = 0
        self.rot_speed = random.uniform(-8, -2) if is_left else random.uniform(2, 8)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.angle += self.rot_speed

    def draw(self, surface):
        if not self.original_image:
            return
        rotated_img = pygame.transform.rotate(self.original_image, self.angle)
        rect = rotated_img.get_rect(center=(int(self.x), int(self.y)))
        surface.blit(rotated_img, rect.topleft)

    def is_out_of_bounds(self):
        return self.y > 1000 * self.scale


class ExplosionEffect:
    """Эффект взрыва бомбы"""

    def __init__(self, x, y, image):
        self.x = x
        self.y = y
        self.image = image
        self.timer = 20  # Время показа в кадрах

    def update(self):
        self.timer -= 1

    def draw(self, surface):
        if self.image and self.timer > 0:
            rect = self.image.get_rect(center=(int(self.x), int(self.y)))
            surface.blit(self.image, rect.topleft)
