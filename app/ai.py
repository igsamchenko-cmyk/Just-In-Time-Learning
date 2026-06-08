from abc import ABC, abstractmethod
from dataclasses import dataclass
import json
from typing import Any

import httpx

from app.config import settings
from app.prompts import (
    ANSWER_EVALUATION_SYSTEM_PROMPT,
    COURSE_PLAN_SYSTEM_PROMPT,
    MODULE_CONTENT_SYSTEM_PROMPT,
)


@dataclass
class CoursePlanModule:
    position: int
    title: str
    short_description: str
    learning_goal: str


@dataclass
class CoursePlan:
    course_title: str
    needs_clarification: bool
    clarifying_questions: list[str]
    safety_status: str
    modules: list[CoursePlanModule]


@dataclass
class GeneratedModuleContent:
    content: str
    example: str
    task_type: str
    practical_task: str
    correct_answer_criteria: str


@dataclass
class EvaluationResult:
    is_correct: bool
    feedback: str
    hint: str | None
    explanation: str | None
    next_action: str


class AIProvider(ABC):
    @abstractmethod
    def generate_course_plan(self, user_request: str, user_notes: str | None = None) -> CoursePlan:
        raise NotImplementedError

    @abstractmethod
    def generate_module_content(
        self,
        course_title: str,
        module_title: str,
        learning_goal: str,
        previous_feedback: list[str],
    ) -> GeneratedModuleContent:
        raise NotImplementedError

    @abstractmethod
    def evaluate_answer(
        self,
        task: str,
        criteria: str,
        answer: str,
        attempt_number: int,
    ) -> EvaluationResult:
        raise NotImplementedError


class MockProvider(AIProvider):
    blocked_keywords = {
        "злам",
        "хакнути",
        "вибухівка",
        "зброя",
        "наркотики",
        "шкідливий код",
    }

    def generate_course_plan(self, user_request: str, user_notes: str | None = None) -> CoursePlan:
        normalized = user_request.lower()
        if any(keyword in normalized for keyword in self.blocked_keywords):
            return CoursePlan(
                course_title="Безпечний освітній огляд",
                needs_clarification=False,
                clarifying_questions=[],
                safety_status="educational_only",
                modules=[],
            )

        if len(user_request.strip()) < 18:
            return CoursePlan(
                course_title="Потрібне уточнення",
                needs_clarification=True,
                clarifying_questions=[
                    "Який результат ти хочеш отримати після навчання?",
                    "Що ти вже знаєш з цієї теми?",
                    "Скільки часу готовий приділити навчанню?",
                ],
                safety_status="allowed",
                modules=[],
            )

        topic = user_request.strip().rstrip(".")
        return CoursePlan(
            course_title=f"Мікрокурс: {topic[:90]}",
            needs_clarification=False,
            clarifying_questions=[],
            safety_status="allowed",
            modules=[
                CoursePlanModule(
                    1,
                    "Орієнтація в темі",
                    "Розберемо ключові поняття, межі задачі та очікуваний результат.",
                    "Сформулювати практичну ціль і зрозуміти базову карту теми.",
                ),
                CoursePlanModule(
                    2,
                    "Базові інструменти і поняття",
                    "Зберемо мінімальний словник і набір інструментів для старту.",
                    "Впевнено пояснити основні терміни і вибрати першу дію.",
                ),
                CoursePlanModule(
                    3,
                    "Практичний сценарій",
                    "Пройдемо ситуацію, схожу на реальну робочу задачу.",
                    "Прийняти рішення в сценарії і пояснити логіку вибору.",
                ),
                CoursePlanModule(
                    4,
                    "Типові помилки",
                    "Побачимо, де найчастіше помиляються, і як себе перевіряти.",
                    "Розпізнати помилку та запропонувати виправлення.",
                ),
                CoursePlanModule(
                    5,
                    "Мініпроєкт і підсумок",
                    "Зберемо знання в невеликий завершений результат.",
                    "Самостійно виконати фінальний крок і описати наступні дії.",
                ),
            ],
        )

    def generate_module_content(
        self,
        course_title: str,
        module_title: str,
        learning_goal: str,
        previous_feedback: list[str],
    ) -> GeneratedModuleContent:
        feedback_note = ""
        if previous_feedback:
            feedback_note = " Врахуй попередній фідбек: спочатку назви припущення, а потім дію."

        return GeneratedModuleContent(
            content=(
                f"У цьому модулі '{module_title}' ми рухаємося короткими практичними кроками. "
                f"Головна ціль: {learning_goal} Почни з того, щоб назвати контекст задачі, "
                "обмеження і першу безпечну дію. Не намагайся вивчити все одразу: для JIT-навчання "
                "важливо дійти до найближчого корисного рішення."
                f"{feedback_note}"
            ),
            example=(
                "Приклад підходу: якщо задача здається великою, спочатку визнач, який результат "
                "потрібен сьогодні, які дані вже є, і що можна перевірити без ризику."
            ),
            task_type="scenario",
            practical_task=(
                f"Сценарій: ти проходиш модуль '{module_title}' у курсі '{course_title}'. "
                "Опиши, яку першу практичну дію зробиш, чому саме її, і як перевіриш, що рухаєшся правильно."
            ),
            correct_answer_criteria=(
                "Відповідь має містити конкретну першу дію, коротке пояснення причини "
                "і спосіб перевірки результату."
            ),
        )

    def evaluate_answer(
        self,
        task: str,
        criteria: str,
        answer: str,
        attempt_number: int,
    ) -> EvaluationResult:
        normalized = answer.lower()
        has_action = len(answer.strip()) >= 35
        has_reason = any(word in normalized for word in ["бо", "тому", "щоб", "оскільки"])
        has_check = any(word in normalized for word in ["перевір", "результат", "тест", "побач", "оцін"])
        is_correct = has_action and has_reason and has_check

        if is_correct:
            return EvaluationResult(
                True,
                "Добре: є дія, причина і спосіб перевірки. Це саме той формат мислення, який потрібен для практичного навчання.",
                None,
                None,
                "unlock_next_module",
            )

        if attempt_number == 1:
            return EvaluationResult(
                False,
                "Ти вже окреслив напрям, але відповідь має бути практичнішою: додай конкретну першу дію, причину і перевірку.",
                None,
                None,
                "try_again",
            )

        if attempt_number == 2:
            return EvaluationResult(
                False,
                "Ще трохи конкретики. Спробуй відповісти в одному реченні за схемою: 'Я зроблю X, бо Y, і перевірю це через Z'.",
                "Використай структуру: дія -> причина -> перевірка.",
                None,
                "show_hint",
            )

        return EvaluationResult(
            False,
            "Покажу правильний підхід, щоб ти міг рухатися далі без застрягання.",
            "Відповідь має бути не загальною, а прив'язаною до першого реального кроку.",
            "Сильна відповідь виглядає так: 'Я спочатку визначу найближчий результат модуля, бо це звужує тему до практичної задачі, і перевірю себе через короткий список критеріїв успіху'.",
            "allow_continue",
        )


class ProviderNotConfigured(AIProvider):
    def __init__(self, provider_name: str, env_var: str) -> None:
        self.provider_name = provider_name
        self.env_var = env_var

    def _raise(self) -> None:
        raise RuntimeError(
            f"{self.provider_name} provider is selected, but {self.env_var} is not configured."
        )

    def generate_course_plan(self, user_request: str, user_notes: str | None = None) -> CoursePlan:
        self._raise()

    def generate_module_content(
        self,
        course_title: str,
        module_title: str,
        learning_goal: str,
        previous_feedback: list[str],
    ) -> GeneratedModuleContent:
        self._raise()

    def evaluate_answer(
        self,
        task: str,
        criteria: str,
        answer: str,
        attempt_number: int,
    ) -> EvaluationResult:
        self._raise()


class GeminiProvider(ProviderNotConfigured):
    endpoint = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def _generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict[str, Any],
    ) -> dict[str, Any]:
        url = self.endpoint.format(model=self.model)
        payload = {
            "systemInstruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.25,
                "responseMimeType": "application/json",
                "responseSchema": schema,
            },
        }
        headers = {
            "Content-Type": "application/json",
            "x-goog-api-key": self.api_key,
        }
        with httpx.Client(timeout=60) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

        try:
            parts = data["candidates"][0]["content"]["parts"]
            text = "".join(part.get("text", "") for part in parts)
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("Gemini response did not include text content") from exc

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Gemini response was not valid JSON") from exc

    def generate_course_plan(self, user_request: str, user_notes: str | None = None) -> CoursePlan:
        data = self._generate_json(
            COURSE_PLAN_SYSTEM_PROMPT,
            (
                "Запит користувача:\n"
                f"{user_request}\n\n"
                "Додаткові нотатки користувача:\n"
                f"{user_notes or 'Немає'}"
            ),
            course_plan_schema(),
        )
        return CoursePlan(
            course_title=str(data["course_title"]),
            needs_clarification=bool(data["needs_clarification"]),
            clarifying_questions=[str(item) for item in data.get("clarifying_questions", [])],
            safety_status=str(data["safety_status"]),
            modules=[
                CoursePlanModule(
                    int(item["position"]),
                    str(item["title"]),
                    str(item["short_description"]),
                    str(item["learning_goal"]),
                )
                for item in data.get("modules", [])
            ],
        )

    def generate_module_content(
        self,
        course_title: str,
        module_title: str,
        learning_goal: str,
        previous_feedback: list[str],
    ) -> GeneratedModuleContent:
        data = self._generate_json(
            MODULE_CONTENT_SYSTEM_PROMPT,
            (
                f"Назва курсу: {course_title}\n"
                f"Назва модуля: {module_title}\n"
                f"Навчальна ціль: {learning_goal}\n"
                "Попередній фідбек:\n"
                + ("\n".join(previous_feedback) if previous_feedback else "Немає")
            ),
            module_content_schema(),
        )
        return GeneratedModuleContent(
            content=str(data["content"]),
            example=str(data["example"]),
            task_type=str(data["task_type"]),
            practical_task=str(data["practical_task"]),
            correct_answer_criteria=str(data["correct_answer_criteria"]),
        )

    def evaluate_answer(
        self,
        task: str,
        criteria: str,
        answer: str,
        attempt_number: int,
    ) -> EvaluationResult:
        data = self._generate_json(
            ANSWER_EVALUATION_SYSTEM_PROMPT,
            (
                f"Завдання: {task}\n"
                f"Критерії: {criteria}\n"
                f"Номер спроби: {attempt_number}\n"
                f"Відповідь користувача: {answer}"
            ),
            answer_evaluation_schema(),
        )
        return EvaluationResult(
            is_correct=bool(data["is_correct"]),
            feedback=str(data["feedback"]),
            hint=data.get("hint"),
            explanation=data.get("explanation"),
            next_action=str(data["next_action"]),
        )


class ClaudeProvider(ProviderNotConfigured):
    def __init__(self) -> None:
        super().__init__("Claude", "CLAUDE_API_KEY")


def get_ai_provider() -> AIProvider:
    if settings.ai_provider == "gemini":
        if settings.gemini_api_key:
            return GeminiProvider(settings.gemini_api_key, settings.gemini_model)
        if settings.ai_fallback_to_mock:
            return MockProvider()
        return ProviderNotConfigured("Gemini", "GEMINI_API_KEY")
    if settings.ai_provider == "claude":
        if not settings.claude_api_key:
            if settings.ai_fallback_to_mock:
                return MockProvider()
            return ClaudeProvider()
    return MockProvider()


def course_plan_schema() -> dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "course_title": {"type": "STRING"},
            "needs_clarification": {"type": "BOOLEAN"},
            "clarifying_questions": {
                "type": "ARRAY",
                "items": {"type": "STRING"},
            },
            "safety_status": {
                "type": "STRING",
                "enum": ["allowed", "educational_only", "blocked"],
            },
            "modules": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "position": {"type": "INTEGER"},
                        "title": {"type": "STRING"},
                        "short_description": {"type": "STRING"},
                        "learning_goal": {"type": "STRING"},
                    },
                    "required": ["position", "title", "short_description", "learning_goal"],
                },
            },
        },
        "required": [
            "course_title",
            "needs_clarification",
            "clarifying_questions",
            "safety_status",
            "modules",
        ],
    }


def module_content_schema() -> dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "content": {"type": "STRING"},
            "example": {"type": "STRING"},
            "task_type": {
                "type": "STRING",
                "enum": ["scenario", "short_answer", "code_or_command"],
            },
            "practical_task": {"type": "STRING"},
            "correct_answer_criteria": {"type": "STRING"},
        },
        "required": [
            "content",
            "example",
            "task_type",
            "practical_task",
            "correct_answer_criteria",
        ],
    }


def answer_evaluation_schema() -> dict[str, Any]:
    return {
        "type": "OBJECT",
        "properties": {
            "is_correct": {"type": "BOOLEAN"},
            "feedback": {"type": "STRING"},
            "hint": {"type": "STRING", "nullable": True},
            "explanation": {"type": "STRING", "nullable": True},
            "next_action": {
                "type": "STRING",
                "enum": [
                    "try_again",
                    "show_hint",
                    "show_explanation",
                    "unlock_next_module",
                    "allow_continue",
                ],
            },
        },
        "required": ["is_correct", "feedback", "hint", "explanation", "next_action"],
    }
