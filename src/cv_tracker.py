import multiprocessing as mp
import cv2
import mediapipe as mp_lib
import math
import time
from collections import deque
import pygame


def cv_worker(out_queue, stop_event, screen_w, screen_h, camera_index, speed_threshold):
    """
    ИЗОЛИРОВАННЫЙ ПРОЦЕСС.
    Инициализируем OpenCV и MediaPipe СТРОГО внутри процесса,
    чтобы полностью избежать GIL-блокировок в Linux.
    """
    cap = cv2.VideoCapture(camera_index)

    # Форсируем честные 60 FPS / HD с камеры
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, screen_w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, screen_h)
    cap.set(cv2.CAP_PROP_FPS, 60)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Без задержек буфера

    mp_hands = mp_lib.solutions.hands
    hands = mp_hands.Hands(
        max_num_hands=1,
        model_complexity=1,
        min_detection_confidence=0.7,
        min_tracking_confidence=0.7
    )

    prev_pos = None

    while not stop_event.is_set():
        ret, frame = cap.read()
        if not ret or frame is None:
            time.sleep(0.001)
            continue

        frame = cv2.flip(frame, 1)
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        results = hands.process(rgb)

        current_pos = None
        speed = 0.0

        if results.multi_hand_landmarks:
            hand_landmarks = results.multi_hand_landmarks[0]
            lm = hand_landmarks.landmark[8]  # Кончик указательного пальца

            current_pos = (int(lm.x * screen_w), int(lm.y * screen_h))

            if prev_pos:
                dx = current_pos[0] - prev_pos[0]
                dy = current_pos[1] - prev_pos[1]
                speed = math.hypot(dx, dy)
            prev_pos = current_pos
        else:
            prev_pos = None

        is_slicing = speed >= speed_threshold

        # Готовим байт-буфер кадра под размер экрана
        frame_resized = cv2.resize(frame, (screen_w, screen_h))
        frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)

        data = {
            'frame_bytes': frame_rgb.tobytes(),
            'pos': current_pos,
            'speed': speed,
            'is_slicing': is_slicing
        }

        # Очищаем очередь от старых кадров, отправляем ТОЛЬКО самый свежий!
        # Это гарантирует 0 мс задержки (Zero Latency)
        while not out_queue.empty():
            try:
                out_queue.get_nowait()
            except:
                break

        out_queue.put(data)

    cap.release()


class CVTrackerMP:
    def __init__(self, screen_w, screen_h, camera_index=0, max_trail_len=14, speed_threshold=15.0):
        self.screen_w = screen_w
        self.screen_h = screen_h
        self.speed_threshold = speed_threshold

        self.queue = mp.Queue(maxsize=2)
        self.stop_event = mp.Event()

        # Запуск отдельного процесса ОС
        self.process = mp.Process(
            target=cv_worker,
            args=(self.queue, self.stop_event, screen_w, screen_h, camera_index, speed_threshold),
            daemon=True
        )
        self.process.start()

        self.trail = deque(maxlen=max_trail_len)
        self.latest_frame_bytes = None
        self.current_pos = None
        self.speed = 0.0
        self.is_slicing = False

    def update(self):
        """Неблокирующее считывание данных из очереди процесса"""
        updated = False
        while not self.queue.empty():
            try:
                data = self.queue.get_nowait()
                self.latest_frame_bytes = data['frame_bytes']
                pos = data['pos']
                self.speed = data['speed']
                self.is_slicing = data['is_slicing']

                if pos:
                    self.current_pos = pos
                    self.trail.appendleft(pos)
                updated = True
            except:
                break

        return self.latest_frame_bytes, updated

    def draw_blade_trail(self, surface, scale=0):
        if len(self.trail) < 2:
            return

        points = list(self.trail)
        n = len(points)

        for i in range(n - 1):
            p1 = (int(points[i][0] * scale), int(points[i][1] * scale))
            p2 = (int(points[i + 1][0] * scale), int(points[i + 1][1] * scale))

            progress = (n - i) / n
            radius = max(2, int((14 * progress) * scale))

            if self.is_slicing:
                color = (255, 255, 255) if i == 0 else (0, 240, 255)
            else:
                color = (180, 180, 200)

            pygame.draw.line(surface, color, p1, p2, radius)
            pygame.draw.circle(surface, color, p1, max(1, radius // 2))

    def release(self):
        self.stop_event.set()
        # Очищаем очередь, чтобы не было блокировки процесса при выходе
        try:
            self.queue.cancel_join_thread()
            while not self.queue.empty():
                self.queue.get_nowait()
            self.queue.close()
        except Exception:
            pass

        if self.process.is_alive():
            self.process.terminate()
            self.process.join(timeout=0.3)
            