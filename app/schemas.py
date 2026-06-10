from datetime import datetime

from pydantic import BaseModel, Field


class CourseCreateRequest(BaseModel):
    goal: str = Field(min_length=3, max_length=4000)
    notes: str | None = Field(default=None, max_length=12000)


class ClarificationAnswerRequest(BaseModel):
    answers: list[str] = Field(min_length=1)


class AttemptCreateRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=8000)


class ModuleSummaryResponse(BaseModel):
    id: int
    position: int
    title: str
    short_description: str
    learning_goal: str
    status: str


class CourseSummaryResponse(BaseModel):
    id: int
    title: str
    original_request: str
    status: str
    safety_status: str
    progress: int
    created_at: datetime
    updated_at: datetime


class CourseDetailResponse(CourseSummaryResponse):
    user_notes: str | None
    modules: list[ModuleSummaryResponse]
    clarifying_questions: list[str]


class ModuleContentResponse(BaseModel):
    content: str
    example: str
    task_type: str
    practical_task: str
    correct_answer_criteria: str


class AttemptResponse(BaseModel):
    id: int
    attempt_number: int
    answer: str
    is_correct: bool
    feedback: str
    hint: str | None
    explanation: str | None
    next_action: str
    created_at: datetime


class ModuleDetailResponse(ModuleSummaryResponse):
    content: ModuleContentResponse | None
    attempts: list[AttemptResponse]


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    avatar_url: str | None


class SystemStatusResponse(BaseModel):
    status: str
    configured_provider: str
    active_provider: str
    gemini_configured: bool
    claude_configured: bool
    gemini_model: str
    total_courses: int
    active_courses: int
    completed_courses: int
    blocked_courses: int
    total_modules: int
    completed_modules: int
    total_attempts: int
    ai_requests_total: int
    ai_requests_ok: int
    ai_requests_error: int
