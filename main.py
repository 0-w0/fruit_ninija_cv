import sys
import pygame
import random

from src.assets_manager import AssetsManager
from src.cv_tracker import CVTrackerMP
from src.game_objects import Fruit, FruitHalf, ExplosionEffect, line_circle_intersection
from src.leaderboard import Leaderboard

# Константы состояний игры
STATE_MENU = 0
STATE_PLAYING = 1
STATE_GAMEOVER = 2


def main():
    pygame.init()

    # Размеры кадра с камеры и масштаб окна
    WIDTH, HEIGHT = 1280, 720
    SCALE = 2.5  # Меняйте масштаб (например, 1.5, 2.0, 2.5) — ВСЁ подстроится автоматически!

    WINDOW_W = int(WIDTH * SCALE)
    WINDOW_H = int(HEIGHT * SCALE)

    screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
    pygame.display.set_caption("Fruit Ninja CV")
    clock = pygame.time.Clock()

    # Инициализация ресурсов и трекера
    assets = AssetsManager(scale=SCALE)
    tracker = CVTrackerMP(screen_w=WIDTH, screen_h=HEIGHT, speed_threshold=8.0, max_trail_len=2)
    leaderboard = Leaderboard()

    # Списки игровых объектов
    fruits = []
    halves = []
    explosions = []

    # Переменные состояния игры
    game_state = STATE_MENU
    player_name = ""
    score = 0
    lives = 3
    spawn_timer = 0

    bg_surface = None
    running = True

    while running:
        # ---------------------------------------------------------
        # 1. ОБРАБОТКА СОБЫТИЙ КЛАВИАТУРЫ И МЫШИ
        # ---------------------------------------------------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False

                # Обработка ввода имени в МЕНЮ
                elif game_state == STATE_MENU:
                    if event.key == pygame.K_RETURN and len(player_name.strip()) > 0:
                        # Запуск игры
                        game_state = STATE_PLAYING
                        score = 0
                        lives = 3
                        fruits.clear()
                        halves.clear()
                        explosions.clear()
                    elif event.key == pygame.K_BACKSPACE:
                        player_name = player_name[:-1]
                    else:
                        if len(player_name) < 12 and event.unicode.isprintable():
                            player_name += event.unicode

                # Обработка выхода из GAME OVER
                elif game_state == STATE_GAMEOVER:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        game_state = STATE_MENU
                        # player_name = ""

        # ---------------------------------------------------------
        # 2. ПОЛУЧЕНИЕ И МАСШТАБИРОВАНИЕ КАДРА С КАМЕРЫ
        # ---------------------------------------------------------
        frame_bytes, has_new_frame = tracker.update()
        if frame_bytes and has_new_frame:
            raw_bg = pygame.image.frombuffer(frame_bytes, (WIDTH, HEIGHT), "RGB")
            bg_surface = pygame.transform.scale(raw_bg, (WINDOW_W, WINDOW_H))

        if bg_surface:
            screen.blit(bg_surface, (0, 0))
        else:
            screen.fill((30, 30, 30))

        # Отрисовка полупрозрачного "Стола"
        table_y = WINDOW_H - int(90 * SCALE)
        table_surface = pygame.Surface((WINDOW_W, int(90 * SCALE)), pygame.SRCALPHA)
        table_surface.fill((0, 0, 0, 90))
        screen.blit(table_surface, (0, table_y))
        pygame.draw.line(screen, (0, 255, 200), (0, table_y), (WINDOW_W, table_y), 2)

        # ---------------------------------------------------------
        # 3. ИГРОВАЯ ЛОГИКА (СПАВН И ОБНОВЛЕНИЕ ФРУКТОВ)
        # ---------------------------------------------------------
        # Подготовка точек шлейфа ножа с учетом SCALE
        scaled_trail = []
        if len(tracker.trail) >= 2:
            scaled_trail = [(int(pt[0] * SCALE), int(pt[1] * SCALE)) for pt in tracker.trail]

        # Спавн фруктов ТОЛЬКО в состоянии игры
        if game_state == STATE_PLAYING:
            spawn_timer += 1
            if spawn_timer > 50:  # Раз в ~1 сек
                spawn_timer = 0
                if len(fruits) < 4:
                    fruits.append(Fruit(WINDOW_W, WINDOW_H, SCALE, assets))

        # Движение и детекция разрезов
        for fruit in fruits[:]:
            fruit.update()
            fruit.draw(screen)

            # Проверка разрезания
            if game_state == STATE_PLAYING and tracker.is_slicing and len(scaled_trail) >= 2:
                is_hit = False

                for i in range(min(5, len(scaled_trail) - 1)):
                    p1 = scaled_trail[i]
                    p2 = scaled_trail[i + 1]
                    hit_radius = fruit.radius + int(20 * SCALE)
                    if line_circle_intersection(p1, p2, (fruit.x, fruit.y), hit_radius):
                        is_hit = True
                        break

                if is_hit:
                    fruit.sliced = True
                    fruits.remove(fruit)

                    if fruit.type == "bomb":
                        lives -= 1
                        explosions.append(ExplosionEffect(fruit.x, fruit.y, assets.get("explosion.png")))

                        # Если жизни закончились от взрыва бомбы — завершаем игру
                        if lives <= 0:
                            game_state = STATE_GAMEOVER
                            leaderboard.add_score(player_name, score)
                    else:
                        score += 10
                        h1 = assets.get(fruit.half1_name)
                        h2 = assets.get(fruit.half2_name)
                        halves.append(FruitHalf(fruit.x, fruit.y, h1, is_left=True, scale=SCALE))
                        halves.append(FruitHalf(fruit.x, fruit.y, h2, is_left=False, scale=SCALE))

            # Проверка улетания фрукта за нижнюю границу (Пропуск!)
            elif fruit.is_out_of_bounds():
                fruits.remove(fruit)
                # if game_state == STATE_PLAYING:
                #     if fruit.type != "bomb":
                #         lives -= 1
                #         # Проверка конца игры
                #         if lives <= 0:
                #             game_state = STATE_GAMEOVER
                #             leaderboard.add_score(player_name, score)

        # Обновление и отрисовка половинок
        for half in halves[:]:
            half.update()
            half.draw(screen)
            if half.is_out_of_bounds():
                halves.remove(half)

        # Эффекты взрывов
        for exp in explosions[:]:
            exp.update()
            exp.draw(screen)
            if exp.timer <= 0:
                explosions.remove(exp)

        # Отрисовка следа от ножа
        tracker.draw_blade_trail(screen, scale=SCALE)

        # ---------------------------------------------------------
        # 4. ОТРИСОВКА ИНТЕРФЕЙСА (HUD / MENU / GAMEOVER)
        # ---------------------------------------------------------
        font_large = pygame.font.SysFont("Arial", int(36 * SCALE), bold=True)
        font_small = pygame.font.SysFont("Arial", int(22 * SCALE), bold=True)

        # А. ЭКРАН МЕНЮ (Ввод имени)
        if game_state == STATE_MENU:
            overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            title_surf = font_large.render("FRUIT NINJA CV", True, (255, 215, 0))
            prompt_surf = font_small.render("Введите ваше имя:", True, (255, 255, 255))
            name_surf = font_large.render(player_name + "_", True, (0, 255, 200))
            start_surf = font_small.render("Нажмите ENTER для старта!", True, (200, 200, 200))

            screen.blit(title_surf, (WINDOW_W // 2 - title_surf.get_width() // 2, int(100 * SCALE)))
            screen.blit(prompt_surf, (WINDOW_W // 2 - prompt_surf.get_width() // 2, int(180 * SCALE)))
            screen.blit(name_surf, (WINDOW_W // 2 - name_surf.get_width() // 2, int(230 * SCALE)))
            screen.blit(start_surf, (WINDOW_W // 2 - start_surf.get_width() // 2, int(300 * SCALE)))

        # Б. ИГРОВОЙ ИНТЕРФЕЙС (HUD)
        elif game_state == STATE_PLAYING:
            # Счет
            score_surf = font_small.render(f"{player_name} | Очки: {score}", True, (255, 215, 0))
            pygame.draw.rect(screen, (0, 0, 0), (20, 20, score_surf.get_width() + 20, int(40 * SCALE)))
            screen.blit(score_surf, (30, 25))

            # Жизни
            hearts_str = " ".join(["<3" for _ in range(lives)])
            lives_surf = font_small.render(f"Жизни: {hearts_str}", True, (255, 50, 50))
            pygame.draw.rect(screen, (0, 0, 0), (WINDOW_W - lives_surf.get_width() - 40, 20, lives_surf.get_width() + 20, int(40 * SCALE)))
            screen.blit(lives_surf, (WINDOW_W - lives_surf.get_width() - 30, 25))

        # В. ЭКРАН GAME OVER И ЛИДЕРБОРД
        elif game_state == STATE_GAMEOVER:
            overlay = pygame.Surface((WINDOW_W, WINDOW_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 210))
            screen.blit(overlay, (0, 0))

            # 1. Заголовки и заработанные очки
            go_surf = font_large.render("ИГРА ОКОНЧЕНА!", True, (255, 50, 50))
            player_surf = font_small.render(f"Игрок: {player_name}", True, (255, 255, 255))
            # Крупная яркая надпись с итоговыми очками:
            result_surf = font_large.render(f"Вы заработали: {score} очков!", True, (255, 215, 0))

            screen.blit(go_surf, (WINDOW_W // 2 - go_surf.get_width() // 2, int(30 * SCALE)))
            screen.blit(player_surf, (WINDOW_W // 2 - player_surf.get_width() // 2, int(75 * SCALE)))
            screen.blit(result_surf, (WINDOW_W // 2 - result_surf.get_width() // 2, int(110 * SCALE)))

            # 2. Таблица лидеров (Топ-5)
            lb_title = font_small.render("--- ТОП-5 ЛИДЕРОВ ---", True, (0, 255, 200))
            screen.blit(lb_title, (WINDOW_W // 2 - lb_title.get_width() // 2, int(160 * SCALE)))

            top_scores = leaderboard.get_top(5)
            for idx, item in enumerate(top_scores):
                row_text = f"{idx + 1}. {item['name']} — {item['score']} очков"
                row_surf = font_small.render(row_text, True, (230, 230, 230))
                screen.blit(row_surf, (WINDOW_W // 2 - row_surf.get_width() // 2, int((195 + idx * 28) * SCALE)))

            # 3. Инструкция по перезапуску
            restart_surf = font_small.render("Нажмите ENTER для выхода в меню", True, (200, 200, 200))
            screen.blit(restart_surf, (WINDOW_W // 2 - restart_surf.get_width() // 2, int(345 * SCALE)))

        pygame.display.flip()
        clock.tick(30)

    # Завершение процессов
    tracker.release()
    pygame.quit()
    sys.exit(0)


if __name__ == '__main__':
    main()
