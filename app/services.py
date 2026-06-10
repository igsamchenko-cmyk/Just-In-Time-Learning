from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.ai import get_ai_provider
from app.config import settings
from app.models import AIRequest, Attempt, Course, CourseClarification, Module, ModuleContent, User


def log_ai_request(
    db: Session,
    user_id: int | None,
    request_type: str,
    status: str,
    course_id: int | None = None,
    module_id: int | None = None,
) -> None:
    db.add(
        AIRequest(
            user_id=user_id,
            course_id=course_id,
            module_id=module_id,
            provider=settings.ai_provider,
            request_type=request_type,
            status=status,
        )
    )


def ai_runtime_status() -> dict[str, str | bool]:
    gemini_configured = bool(settings.gemini_api_key)
    claude_configured = bool(settings.claude_api_key)
    active_provider = settings.ai_provider
    if settings.ai_provider == "gemini" and not gemini_configured and settings.ai_fallback_to_mock:
        active_provider = "mock"
    if settings.ai_provider == "claude" and not claude_configured and settings.ai_fallback_to_mock:
        active_provider = "mock"

    return {
        "status": "ok",
        "configured_provider": settings.ai_provider,
        "active_provider": active_provider,
        "gemini_configured": gemini_configured,
        "claude_configured": claude_configured,
        "gemini_model": settings.gemini_model,
    }


def user_system_status(db: Session, user: User) -> dict[str, str | bool | int]:
    course_filter = Course.user_id == user.id
    module_filter = Module.course_id.in_(select(Course.id).where(course_filter))

    return {
        **ai_runtime_status(),
        "total_courses": db.scalar(select(func.count(Course.id)).where(course_filter)) or 0,
        "active_courses": db.scalar(
            select(func.count(Course.id)).where(course_filter, Course.status == "active")
        )
        or 0,
        "completed_courses": db.scalar(
            select(func.count(Course.id)).where(course_filter, Course.status == "completed")
        )
        or 0,
        "blocked_courses": db.scalar(
            select(func.count(Course.id)).where(course_filter, Course.status == "blocked")
        )
        or 0,
        "total_modules": db.scalar(select(func.count(Module.id)).where(module_filter)) or 0,
        "completed_modules": db.scalar(
            select(func.count(Module.id)).where(module_filter, Module.status == "completed")
        )
        or 0,
        "total_attempts": db.scalar(
            select(func.count(Attempt.id)).where(Attempt.user_id == user.id)
        )
        or 0,
        "ai_requests_total": db.scalar(
            select(func.count(AIRequest.id)).where(AIRequest.user_id == user.id)
        )
        or 0,
        "ai_requests_ok": db.scalar(
            select(func.count(AIRequest.id)).where(
                AIRequest.user_id == user.id,
                AIRequest.status == "ok",
            )
        )
        or 0,
        "ai_requests_error": db.scalar(
            select(func.count(AIRequest.id)).where(
                AIRequest.user_id == user.id,
                AIRequest.status == "error",
            )
        )
        or 0,
    }


def course_progress(course: Course) -> int:
    if not course.modules:
        return 0
    completed = sum(1 for module in course.modules if module.status == "completed")
    return round(completed / len(course.modules) * 100)


def render_course_markdown(course: Course) -> str:
    lines = [
        f"# {course.title}",
        "",
        "## Навчальна ціль",
        "",
        course.original_request,
        "",
    ]

    if course.user_notes:
        lines.extend(["## Нотатки користувача", "", course.user_notes, ""])

    lines.extend(
        [
            "## Прогрес",
            "",
            f"- Статус курсу: `{course.status}`",
            f"- Статус безпеки: `{course.safety_status}`",
            f"- Прогрес: {course_progress(course)}%",
            "",
            "## Модулі",
            "",
        ]
    )

    if not course.modules:
        lines.extend(["Поки що модулі не згенеровані.", ""])
        return "\n".join(lines).strip() + "\n"

    for module in course.modules:
        lines.extend(
            [
                f"### Модуль {module.position}. {module.title}",
                "",
                f"**Статус:** `{module.status}`",
                "",
                f"**Опис:** {module.short_description}",
                "",
                f"**Ціль:** {module.learning_goal}",
                "",
            ]
        )

        if module.content:
            lines.extend(
                [
                    "#### Матеріал",
                    "",
                    module.content.content,
                    "",
                    "#### Приклад",
                    "",
                    module.content.example,
                    "",
                    "#### Практичне завдання",
                    "",
                    module.content.practical_task,
                    "",
                    "#### Критерії відповіді",
                    "",
                    module.content.correct_answer_criteria,
                    "",
                ]
            )

        if module.attempts:
            lines.extend(["#### Спроби та фідбек", ""])
            for attempt in module.attempts:
                result = "правильно" if attempt.is_correct else "потрібне доопрацювання"
                lines.extend(
                    [
                        f"- Спроба {attempt.attempt_number}: **{result}**",
                        f"  - Відповідь: {attempt.answer}",
                        f"  - Фідбек: {attempt.feedback}",
                    ]
                )
                if attempt.hint:
                    lines.append(f"  - Підказка: {attempt.hint}")
                if attempt.explanation:
                    lines.append(f"  - Пояснення: {attempt.explanation}")
            lines.append("")

    return "\n".join(lines).strip() + "\n"


def create_course_for_user(db: Session, user: User, goal: str, notes: str | None) -> Course:
    provider = get_ai_provider()
    try:
        plan = provider.generate_course_plan(goal, notes)
        log_ai_request(db, user.id, "generate_course_plan", "ok")
    except Exception:
        log_ai_request(db, user.id, "generate_course_plan", "error")
        db.commit()
        raise

    course = Course(
        user_id=user.id,
        title=plan.course_title,
        original_request=goal,
        user_notes=notes or None,
        status="needs_clarification" if plan.needs_clarification else "active",
        safety_status=plan.safety_status,
    )
    db.add(course)
    db.flush()

    if plan.safety_status != "allowed":
        course.status = "blocked"
        db.commit()
        db.refresh(course)
        return course

    for question in plan.clarifying_questions:
        db.add(CourseClarification(course_id=course.id, question=question))

    for item in plan.modules:
        db.add(
            Module(
                course_id=course.id,
                position=item.position,
                title=item.title,
                short_description=item.short_description,
                learning_goal=item.learning_goal,
                status="available" if item.position == 1 else "locked",
            )
        )

    db.commit()
    db.refresh(course)
    return course


def answer_course_clarifications(db: Session, course: Course, answers: list[str]) -> Course:
    for clarification, answer in zip(course.clarifications, answers):
        clarification.answer = answer

    provider = get_ai_provider()
    combined_request = course.original_request + "\n" + "\n".join(answers)
    try:
        plan = provider.generate_course_plan(combined_request, course.user_notes)
        log_ai_request(db, course.user_id, "answer_clarifications", "ok", course.id)
    except Exception:
        log_ai_request(db, course.user_id, "answer_clarifications", "error", course.id)
        db.commit()
        raise

    course.title = plan.course_title
    course.status = "active" if plan.safety_status == "allowed" else "blocked"
    course.safety_status = plan.safety_status

    for module in list(course.modules):
        db.delete(module)
    db.flush()

    if plan.safety_status == "allowed":
        for item in plan.modules:
            db.add(
                Module(
                    course_id=course.id,
                    position=item.position,
                    title=item.title,
                    short_description=item.short_description,
                    learning_goal=item.learning_goal,
                    status="available" if item.position == 1 else "locked",
                )
            )

    db.commit()
    db.refresh(course)
    return course


def ensure_module_content(db: Session, course: Course, module: Module) -> Module:
    if module.content:
        return module

    provider = get_ai_provider()
    previous_feedback = [
        attempt.feedback
        for attempt in db.scalars(
            select(Attempt)
            .join(Module)
            .where(Module.course_id == course.id, Attempt.user_id == course.user_id)
            .order_by(Attempt.created_at.desc())
            .limit(5)
        ).all()
    ]
    try:
        generated = provider.generate_module_content(
            course.title,
            module.title,
            module.learning_goal,
            previous_feedback,
        )
        log_ai_request(db, course.user_id, "generate_module_content", "ok", course.id, module.id)
    except Exception:
        log_ai_request(db, course.user_id, "generate_module_content", "error", course.id, module.id)
        db.commit()
        raise
    db.add(
        ModuleContent(
            module_id=module.id,
            content=generated.content,
            example=generated.example,
            task_type=generated.task_type,
            practical_task=generated.practical_task,
            correct_answer_criteria=generated.correct_answer_criteria,
        )
    )
    module.status = "in_progress"
    db.commit()
    db.refresh(module)
    return module


def submit_module_attempt(db: Session, course: Course, module: Module, answer: str) -> Attempt:
    if not module.content:
        raise ValueError("Module content must be generated before answering")

    attempt_number = (
        db.scalar(
            select(func.count(Attempt.id)).where(
                Attempt.module_id == module.id,
                Attempt.user_id == course.user_id,
            )
        )
        + 1
    )
    provider = get_ai_provider()
    try:
        result = provider.evaluate_answer(
            module.content.practical_task,
            module.content.correct_answer_criteria,
            answer,
            attempt_number,
        )
        log_ai_request(db, course.user_id, "evaluate_answer", "ok", course.id, module.id)
    except Exception:
        log_ai_request(db, course.user_id, "evaluate_answer", "error", course.id, module.id)
        db.commit()
        raise
    attempt = Attempt(
        module_id=module.id,
        user_id=course.user_id,
        answer=answer,
        attempt_number=attempt_number,
        is_correct=result.is_correct,
        feedback=result.feedback,
        hint=result.hint,
        explanation=result.explanation,
        next_action=result.next_action,
    )
    db.add(attempt)

    if result.next_action == "unlock_next_module":
        unlock_next_module(db, course, module)

    db.commit()
    db.refresh(attempt)
    return attempt


def unlock_next_module(db: Session, course: Course, module: Module) -> None:
    module.status = "completed"
    next_module = db.scalar(
        select(Module)
        .where(Module.course_id == course.id, Module.position == module.position + 1)
        .limit(1)
    )
    if next_module:
        next_module.status = "available"
        course.current_module_id = next_module.id
    else:
        course.status = "completed"
        course.current_module_id = module.id


def continue_after_explanation(db: Session, course: Course, module: Module) -> bool:
    latest_attempt = db.scalar(
        select(Attempt)
        .where(Attempt.module_id == module.id, Attempt.user_id == course.user_id)
        .order_by(Attempt.created_at.desc())
        .limit(1)
    )
    if not latest_attempt or latest_attempt.next_action != "allow_continue":
        return False

    unlock_next_module(db, course, module)
    db.commit()
    return True
