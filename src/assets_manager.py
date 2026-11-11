import pygame
import os


class AssetsManager:
    def __init__(self, scale=1.0, assets_dir="images", base_size=(130, 130)):
        self.assets_dir = assets_dir
        self.scale = scale
        # Базовый размер множится на SCALE
        self.target_size = (int(base_size[0] * scale), int(base_size[1] * scale))
        self.images = {}
        self.load_all()

    def load_all(self):
        file_list = [
            "apple.png", "apple_half_1.png", "apple_half_2.png",
            "banana.png", "banana_half_1.png", "banana_half_2.png",
            "coconut.png", "coconut_half_1.png", "coconut_half_2.png",
            "bomb.png", "explosion.png"
        ]

        for filename in file_list:
            path = os.path.join(self.assets_dir, filename)
            if not os.path.exists(path):
                print(f"[ОШИБКА] Файл не найден: {path}")
                continue

            img = pygame.image.load(path).convert_alpha()

            # Пропорции с учетом SCALE
            if "banana" in filename:
                size = (int(110 * self.scale), int(90 * self.scale)) if "half" not in filename else (
                    int(60 * self.scale), int(80 * self.scale))
            elif "half" in filename:
                size = (int(self.target_size[0] * 0.55), self.target_size[1])
            elif filename == "explosion.png":
                size = (int(220 * self.scale), int(220 * self.scale))
            else:
                size = self.target_size

            self.images[filename] = pygame.transform.smoothscale(img, size)

        print(f"[AssetsManager] Загружены ресурсы с масштабом SCALE={self.scale}")

    def get(self, name):
        return self.images.get(name)
