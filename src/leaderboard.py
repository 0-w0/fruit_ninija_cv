import json
import os

class Leaderboard:
    def __init__(self, filename="leaderboard.json"):
        self.filename = filename
        self.scores = self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def save(self):
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.scores, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[Leaderboard Error] {e}")

    def add_score(self, name, score):
        clean_name = name.strip() if name.strip() else "Первокурсник"
        self.scores.append({"name": clean_name, "score": score})
        # Сортировка по убыванию очков
        self.scores.sort(key=lambda x: x["score"], reverse=True)
        # Оставляем только Топ-10
        self.scores = self.scores[:10]
        self.save()

    def get_top(self, limit=5):
        return self.scores[:limit]
