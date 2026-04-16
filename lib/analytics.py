"""Модуль для трекинга использования токенов и статистики."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class TokenAnalytics:
    """Трекинг статистики использования токенов."""

    def __init__(self, storage_path: str = "data/analytics.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(exist_ok=True)
        self.data = self._load_data()

    def track_token_usage(self, user_id: str, model: str,
                          input_tokens: int, output_tokens: int):
        if user_id not in self.data:
            self.data[user_id] = []
        self.data[user_id].append({
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "input": input_tokens,
            "output": output_tokens,
            "total": input_tokens + output_tokens
        })
        self._save_data()

    def get_stats(self, user_id: str) -> Dict:
        if user_id not in self.data:
            return {"total_tokens": 0, "requests": 0}

        sessions = self.data[user_id]
        return {
            "total_tokens": sum(s["total"] for s in sessions),
            "input_tokens": sum(s["input"] for s in sessions),
            "output_tokens": sum(s["output"] for s in sessions),
            "requests": len(sessions),
            "models": list(set(s["model"] for s in sessions))
        }

    def _load_data(self) -> Dict:
        if self.storage_path.exists():
            return json.loads(self.storage_path.read_text())
        return {}

    def _save_data(self):
        self.storage_path.write_text(json.dumps(self.data, indent=2))


# Глобальная аналитика — АНТИПАТТЕРН: mutable глобальное состояние
analytics = TokenAnalytics()
