import os
import unittest


os.environ["DATABASE_URL"] = "sqlite:///./test_learning_mvp.db"
os.environ["AI_PROVIDER"] = "mock"
os.environ["SESSION_SECRET"] = "test-session-secret"

from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


class MVPFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)
        self.client = TestClient(app)
        response = self.client.post("/login/demo", follow_redirects=False)
        self.assertEqual(response.status_code, 303)

    def tearDown(self) -> None:
        self.client.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()

    def test_health_reports_mock_provider(self) -> None:
        response = self.client.get("/api/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["active_provider"], "mock")

    def test_course_creation_module_completion_and_progress(self) -> None:
        response = self.client.post(
            "/api/courses",
            json={
                "goal": "Хочу навчитися планувати робочий день без перевантаження",
                "notes": "Маю багато задач і часто перемикаюся.",
            },
        )
        self.assertEqual(response.status_code, 200)
        course = response.json()
        self.assertEqual(course["status"], "active")
        self.assertGreaterEqual(len(course["modules"]), 3)
        self.assertEqual(course["modules"][0]["status"], "available")
        self.assertEqual(course["modules"][1]["status"], "locked")

        course_id = course["id"]
        module_id = course["modules"][0]["id"]
        module_response = self.client.get(f"/api/courses/{course_id}/modules/{module_id}")
        self.assertEqual(module_response.status_code, 200)
        self.assertIsNotNone(module_response.json()["content"])

        attempt_response = self.client.post(
            f"/api/courses/{course_id}/modules/{module_id}/attempts",
            json={
                "answer": (
                    "Я спочатку визначу першу практичну дію, бо це допоможе "
                    "не розпорошуватися, і перевірю результат через короткий список критеріїв."
                )
            },
        )
        self.assertEqual(attempt_response.status_code, 200)
        self.assertTrue(attempt_response.json()["is_correct"])
        self.assertEqual(attempt_response.json()["next_action"], "unlock_next_module")

        updated_course = self.client.get(f"/api/courses/{course_id}").json()
        self.assertEqual(updated_course["modules"][0]["status"], "completed")
        self.assertEqual(updated_course["modules"][1]["status"], "available")
        self.assertGreater(updated_course["progress"], 0)

    def test_short_goal_creates_clarifying_questions(self) -> None:
        response = self.client.post("/api/courses", json={"goal": "Python", "notes": ""})

        self.assertEqual(response.status_code, 200)
        course = response.json()
        self.assertEqual(course["status"], "needs_clarification")
        self.assertEqual(len(course["clarifying_questions"]), 3)
        self.assertEqual(course["modules"], [])

    def test_risky_goal_is_blocked_to_safe_mode(self) -> None:
        response = self.client.post(
            "/api/courses",
            json={"goal": "Хочу навчитися зламати сайт", "notes": ""},
        )

        self.assertEqual(response.status_code, 200)
        course = response.json()
        self.assertEqual(course["status"], "blocked")
        self.assertEqual(course["safety_status"], "educational_only")
        self.assertEqual(course["modules"], [])


if __name__ == "__main__":
    unittest.main()
