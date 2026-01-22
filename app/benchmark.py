#!/usr/bin/env python3
"""
День 28: Бенчмарк для оптимизации LLM на задаче Sentiment Analysis.

Сравнивает разные конфигурации модели:
- Temperature
- Context window (num_ctx)
- System prompt (zero-shot vs few-shot)
- Квантование (q4 vs q8)
"""

import requests
import json
import time
from dataclasses import dataclass
from typing import List, Dict, Optional


# === Тестовый датасет ===
TEST_DATA = [
    # Positive (7)
    ("Отличный товар, очень доволен покупкой!", "positive"),
    ("Быстрая доставка, всё работает идеально", "positive"),
    ("Рекомендую всем, лучшее соотношение цена-качество", "positive"),
    ("Превзошёл все мои ожидания!", "positive"),
    ("Качество на высоте, буду заказывать ещё", "positive"),
    ("Супер! Именно то, что искал", "positive"),
    ("Прекрасный сервис и отличный продукт", "positive"),
    # Negative (7)
    ("Ужасное качество, деньги на ветер", "negative"),
    ("Доставка задержалась на неделю, товар пришёл повреждённый", "negative"),
    ("Не рекомендую, полное разочарование", "negative"),
    ("Сломался через два дня использования", "negative"),
    ("Абсолютно не соответствует описанию", "negative"),
    ("Худшая покупка в моей жизни", "negative"),
    ("Поддержка не отвечает, проблему не решили", "negative"),
    # Neutral (6)
    ("Товар соответствует описанию", "neutral"),
    ("Обычный товар, ничего особенного", "neutral"),
    ("Доставили вовремя", "neutral"),
    ("Нормальное качество за свою цену", "neutral"),
    ("Пока сложно оценить, время покажет", "neutral"),
    ("Среднее качество, средняя цена", "neutral"),
]


# === System Prompts ===
ZERO_SHOT_PROMPT = """Ты — классификатор тональности текста.
Определи тональность текста: positive, negative или neutral.
Ответь ТОЛЬКО одним словом: positive, negative или neutral."""

FEW_SHOT_PROMPT = """Ты — классификатор тональности текста.
Определи тональность текста: positive, negative или neutral.

Примеры:
- "Отличный товар, очень доволен покупкой!" → positive
- "Ужасное качество, деньги на ветер" → negative
- "Товар соответствует описанию" → neutral

Ответь ТОЛЬКО одним словом: positive, negative или neutral."""


@dataclass
class ExperimentConfig:
    """Конфигурация эксперимента."""
    name: str
    model: str
    temperature: Optional[float] = None
    num_ctx: Optional[int] = None
    system_prompt: Optional[str] = None


@dataclass
class ExperimentResult:
    """Результат эксперимента."""
    config: ExperimentConfig
    correct: int
    total: int
    avg_time: float
    format_errors: int

    @property
    def accuracy(self) -> float:
        return self.correct / self.total * 100 if self.total > 0 else 0


class OllamaBenchmark:
    """Бенчмарк для Ollama моделей."""

    def __init__(self, host: str = "http://localhost:11434"):
        self.host = host
        self.session = requests.Session()

    def list_models(self) -> List[str]:
        """Возвращает список доступных моделей."""
        try:
            response = self.session.get(f"{self.host}/api/tags")
            response.raise_for_status()
            return [m["name"] for m in response.json().get("models", [])]
        except Exception as e:
            print(f"Ошибка получения списка моделей: {e}")
            return []

    def generate(
        self,
        prompt: str,
        model: str,
        system: Optional[str] = None,
        temperature: Optional[float] = None,
        num_ctx: Optional[int] = None,
    ) -> tuple[str, float]:
        """
        Генерирует ответ (не streaming).
        Возвращает (ответ, время_в_секундах).
        """
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }

        options = {}
        if temperature is not None:
            options["temperature"] = temperature
        if num_ctx is not None:
            options["num_ctx"] = num_ctx
        if options:
            payload["options"] = options

        start_time = time.time()
        response = self.session.post(
            f"{self.host}/api/chat",
            json=payload,
            timeout=120,
        )
        response.raise_for_status()
        elapsed = time.time() - start_time

        data = response.json()
        content = data.get("message", {}).get("content", "")
        return content.strip(), elapsed

    def parse_sentiment(self, response: str) -> Optional[str]:
        """Извлекает sentiment из ответа модели."""
        response_lower = response.lower().strip()

        # Точное совпадение
        if response_lower in ("positive", "negative", "neutral"):
            return response_lower

        # Поиск ключевых слов
        for sentiment in ("positive", "negative", "neutral"):
            if sentiment in response_lower:
                return sentiment

        return None

    def run_experiment(self, config: ExperimentConfig) -> ExperimentResult:
        """Запускает один эксперимент."""
        print(f"\n--- {config.name} ---")
        print(f"  Модель: {config.model}")

        correct = 0
        total = len(TEST_DATA)
        format_errors = 0
        times = []

        for i, (text, expected) in enumerate(TEST_DATA, 1):
            try:
                response, elapsed = self.generate(
                    prompt=text,
                    model=config.model,
                    system=config.system_prompt,
                    temperature=config.temperature,
                    num_ctx=config.num_ctx,
                )
                times.append(elapsed)

                predicted = self.parse_sentiment(response)
                if predicted is None:
                    format_errors += 1
                    status = "?"
                elif predicted == expected:
                    correct += 1
                    status = "✓"
                else:
                    status = "✗"

                print(f"  [{i:2}/{total}] {status} {expected:8} → {response[:30]}")

            except Exception as e:
                print(f"  [{i:2}/{total}] ! Ошибка: {e}")
                format_errors += 1

        avg_time = sum(times) / len(times) if times else 0

        result = ExperimentResult(
            config=config,
            correct=correct,
            total=total,
            avg_time=avg_time,
            format_errors=format_errors,
        )

        print(f"  Accuracy: {result.accuracy:.0f}% ({correct}/{total})")
        print(f"  Среднее время: {avg_time:.1f} сек")

        return result


def main():
    """Основная функция бенчмарка."""
    print("=" * 60)
    print("День 28: Оптимизация LLM для Sentiment Analysis")
    print("=" * 60)

    benchmark = OllamaBenchmark()

    # Проверяем доступные модели
    models = benchmark.list_models()
    print(f"\nДоступные модели: {models}")

    # Находим gemma2 модели
    gemma_models = [m for m in models if "gemma2" in m.lower() or "gemma" in m.lower()]
    if not gemma_models:
        print("Модели gemma2 не найдены! Скачайте: ollama pull gemma2:2b")
        return

    base_model = gemma_models[0]
    print(f"Используем модель: {base_model}")

    # Конфигурации экспериментов
    experiments = [
        ExperimentConfig(
            name="1. Baseline (без оптимизации)",
            model=base_model,
        ),
        ExperimentConfig(
            name="2. Zero-shot + temp=0.0",
            model=base_model,
            temperature=0.0,
            num_ctx=2048,
            system_prompt=ZERO_SHOT_PROMPT,
        ),
        ExperimentConfig(
            name="3. Few-shot + temp=0.0",
            model=base_model,
            temperature=0.0,
            num_ctx=2048,
            system_prompt=FEW_SHOT_PROMPT,
        ),
    ]

    # Добавляем эксперименты с квантованными моделями если доступны
    q4_models = [m for m in models if "q4" in m.lower() and "gemma" in m.lower()]
    q8_models = [m for m in models if "q8" in m.lower() and "gemma" in m.lower()]

    if q4_models:
        experiments.append(ExperimentConfig(
            name=f"4. Q4 + Few-shot ({q4_models[0]})",
            model=q4_models[0],
            temperature=0.0,
            num_ctx=2048,
            system_prompt=FEW_SHOT_PROMPT,
        ))

    if q8_models:
        experiments.append(ExperimentConfig(
            name=f"5. Q8 + Few-shot ({q8_models[0]})",
            model=q8_models[0],
            temperature=0.0,
            num_ctx=2048,
            system_prompt=FEW_SHOT_PROMPT,
        ))

    # Запуск экспериментов
    results: List[ExperimentResult] = []
    for config in experiments:
        try:
            result = benchmark.run_experiment(config)
            results.append(result)
        except Exception as e:
            print(f"Ошибка эксперимента {config.name}: {e}")

    # Сводная таблица
    print("\n" + "=" * 60)
    print("СВОДНАЯ ТАБЛИЦА")
    print("=" * 60)
    print(f"{'Эксперимент':<35} {'Accuracy':>10} {'Время':>8} {'Улучшение':>12}")
    print("-" * 60)

    baseline_acc = results[0].accuracy if results else 0

    for r in results:
        improvement = r.accuracy - baseline_acc
        imp_str = f"+{improvement:.0f}%" if improvement > 0 else f"{improvement:.0f}%"
        if r == results[0]:
            imp_str = "-"

        print(f"{r.config.name:<35} {r.accuracy:>9.0f}% {r.avg_time:>7.1f}s {imp_str:>12}")

    # Выводы
    print("\n" + "=" * 60)
    print("ВЫВОДЫ")
    print("=" * 60)

    if len(results) >= 3:
        best = max(results, key=lambda r: r.accuracy)
        print(f"• Лучший результат: {best.config.name} ({best.accuracy:.0f}%)")

        if results[2].accuracy > results[1].accuracy:
            diff = results[2].accuracy - results[1].accuracy
            print(f"• Few-shot дал прирост +{diff:.0f}% относительно zero-shot")

        if results[0].accuracy < best.accuracy:
            total_improvement = best.accuracy - results[0].accuracy
            print(f"• Общее улучшение относительно baseline: +{total_improvement:.0f}%")


if __name__ == "__main__":
    main()
