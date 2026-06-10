from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Form, HTTPException, Request

from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app.auth import (
    get_current_user,
    get_or_create_demo_user,
    get_or_create_user_from_google,
    google_oauth_configured,
    oauth,
)
from app.config import settings
from app.database import Base, engine, get_db
from app.models import Attempt, Course, Module, User
from app.schemas import (
    AttemptCreateRequest,
    AttemptResponse,
    ClarificationAnswerRequest,
    CourseCreateRequest,
    CourseDetailResponse,
    CourseSummaryResponse,
    ModuleContentResponse,
    ModuleDetailResponse,
    ModuleSummaryResponse,
    SystemStatusResponse,
    UserResponse,
)
from app.services import (
    ai_runtime_status,
    answer_course_clarifications,
    continue_after_explanation as continue_after_explanation_service,
    course_progress,
    create_course_for_user,
    ensure_module_content,
    AIServiceError,
    render_course_markdown,
    submit_module_attempt,
    user_system_status,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret,
    same_site="lax",
    https_only=False,
)
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.exception_handler(AIServiceError)
async def ai_service_error_handler(request: Request, exc: AIServiceError):
    message = str(exc)
    if request.url.path.startswith("/api/"):
        return JSONResponse(
            status_code=503,
            content={
                "detail": message,
                "retry": True,
            },
        )

    return templates.TemplateResponse(
        "error.html",
        {
            "request": request,
            "title": "AI тимчасово недоступний",
            "message": message,
            "back_url": request.headers.get("referer") or "/",
        },
        status_code=503,
    )


def require_user(request: Request, db: Session) -> User:
    user = get_current_user(request, db)
    if user:
        return user
    raise HTTPException(status_code=401)


def require_owned_course(db: Session, user: User, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if not course or course.user_id != user.id:
        raise HTTPException(status_code=404)
    return course


def require_owned_module(db: Session, course: Course, module_id: int) -> Module:
    module = db.get(Module, module_id)
    if not module or module.course_id != course.id:
        raise HTTPException(status_code=404)
    return module


def serialize_user(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        avatar_url=user.avatar_url,
    )


def serialize_module_summary(module: Module) -> ModuleSummaryResponse:
    return ModuleSummaryResponse(
        id=module.id,
        position=module.position,
        title=module.title,
        short_description=module.short_description,
        learning_goal=module.learning_goal,
        status=module.status,
    )


def serialize_course_summary(course: Course) -> CourseSummaryResponse:
    return CourseSummaryResponse(
        id=course.id,
        title=course.title,
        original_request=course.original_request,
        status=course.status,
        safety_status=course.safety_status,
        progress=course_progress(course),
        created_at=course.created_at,
        updated_at=course.updated_at,
    )


def serialize_course_detail(course: Course) -> CourseDetailResponse:
    summary = serialize_course_summary(course)
    return CourseDetailResponse(
        **summary.model_dump(),
        user_notes=course.user_notes,
        modules=[serialize_module_summary(module) for module in course.modules],
        clarifying_questions=[
            item.question for item in course.clarifications if not item.answer
        ],
    )


def serialize_attempt(attempt: Attempt) -> AttemptResponse:
    return AttemptResponse(
        id=attempt.id,
        attempt_number=attempt.attempt_number,
        answer=attempt.answer,
        is_correct=attempt.is_correct,
        feedback=attempt.feedback,
        hint=attempt.hint,
        explanation=attempt.explanation,
        next_action=attempt.next_action,
        created_at=attempt.created_at,
    )


def serialize_module_detail(module: Module) -> ModuleDetailResponse:
    content = None
    if module.content:
        content = ModuleContentResponse(
            content=module.content.content,
            example=module.content.example,
            task_type=module.content.task_type,
            practical_task=module.content.practical_task,
            correct_answer_criteria=module.content.correct_answer_criteria,
        )

    return ModuleDetailResponse(
        **serialize_module_summary(module).model_dump(),
        content=content,
        attempts=[serialize_attempt(attempt) for attempt in module.attempts],
    )


@app.get("/login")
def login(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "google_enabled": google_oauth_configured(),
        },
    )


@app.post("/login/demo")
def demo_login(request: Request, db: Session = Depends(get_db)):
    user = get_or_create_demo_user(db)
    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=303)


@app.get("/auth/google")
async def google_login(request: Request):
    if not google_oauth_configured():
        return RedirectResponse("/login", status_code=303)
    redirect_uri = request.url_for("google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    if not google_oauth_configured():
        return RedirectResponse("/login", status_code=303)
    token = await oauth.google.authorize_access_token(request)
    profile = token.get("userinfo")
    if profile is None:
        profile = await oauth.google.userinfo(token=token)
    user = get_or_create_user_from_google(db, dict(profile))
    request.session["user_id"] = user.id
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/api/me", response_model=UserResponse)
def api_me(request: Request, db: Session = Depends(get_db)):
    return serialize_user(require_user(request, db))


@app.get("/api/health")
def api_health():
    return ai_runtime_status()


@app.get("/api/system/status", response_model=SystemStatusResponse)
def api_system_status(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    return user_system_status(db, user)


@app.get("/api/courses", response_model=list[CourseSummaryResponse])
def api_courses(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    courses = db.scalars(
        select(Course).where(Course.user_id == user.id).order_by(Course.updated_at.desc())
    ).all()
    return [serialize_course_summary(course) for course in courses]


@app.post("/api/courses", response_model=CourseDetailResponse)
def api_create_course(
    payload: CourseCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    course = create_course_for_user(db, user, payload.goal, payload.notes)
    return serialize_course_detail(course)


@app.get("/api/courses/{course_id}", response_model=CourseDetailResponse)
def api_course(course_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    course = require_owned_course(db, user, course_id)
    return serialize_course_detail(course)


@app.delete("/api/courses/{course_id}", status_code=204)
def api_delete_course(course_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    course = require_owned_course(db, user, course_id)
    db.delete(course)
    db.commit()


@app.get("/api/courses/{course_id}/export.md", response_class=PlainTextResponse)
def api_export_course_markdown(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    course = require_owned_course(db, user, course_id)
    return PlainTextResponse(
        render_course_markdown(course),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="course-{course.id}.md"',
        },
    )


@app.post("/api/courses/{course_id}/clarifications", response_model=CourseDetailResponse)
def api_answer_clarifications(
    course_id: int,
    payload: ClarificationAnswerRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    course = require_owned_course(db, user, course_id)
    answer_course_clarifications(db, course, payload.answers)
    return serialize_course_detail(course)


@app.get(
    "/api/courses/{course_id}/modules/{module_id}",
    response_model=ModuleDetailResponse,
)
def api_module(
    course_id: int,
    module_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    course = require_owned_course(db, user, course_id)
    module = require_owned_module(db, course, module_id)
    if module.status == "locked":
        raise HTTPException(status_code=403, detail="Module is locked")
    module = ensure_module_content(db, course, module)
    return serialize_module_detail(module)


@app.post(
    "/api/courses/{course_id}/modules/{module_id}/attempts",
    response_model=AttemptResponse,
)
def api_submit_attempt(
    course_id: int,
    module_id: int,
    payload: AttemptCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    course = require_owned_course(db, user, course_id)
    module = require_owned_module(db, course, module_id)
    if module.status == "locked":
        raise HTTPException(status_code=403, detail="Module is locked")
    module = ensure_module_content(db, course, module)
    attempt = submit_module_attempt(db, course, module, payload.answer)
    return serialize_attempt(attempt)


@app.post(
    "/api/courses/{course_id}/modules/{module_id}/continue",
    response_model=CourseDetailResponse,
)
def api_continue_after_explanation(
    course_id: int,
    module_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    course = require_owned_course(db, user, course_id)
    module = require_owned_module(db, course, module_id)
    if not continue_after_explanation_service(db, course, module):
        raise HTTPException(status_code=400, detail="Module cannot be continued yet")
    return serialize_course_detail(course)


@app.get("/")
def home(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    courses = db.scalars(
        select(Course).where(Course.user_id == user.id).order_by(Course.updated_at.desc())
    ).all()
    return templates.TemplateResponse(
        "courses.html",
        {
            "request": request,
            "user": user,
            "courses": courses,
            "course_progress": course_progress,
        },
    )


@app.get("/courses/new")
def new_course(request: Request, db: Session = Depends(get_db)):
    if not get_current_user(request, db):
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse("new_course.html", {"request": request})


@app.get("/status")
def system_status(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    return templates.TemplateResponse(
        "status.html",
        {
            "request": request,
            "status": user_system_status(db, user),
        },
    )


@app.post("/courses")
def create_course(
    request: Request,
    goal: str = Form(...),
    notes: str = Form(""),
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    course = create_course_for_user(db, user, goal, notes)
    return RedirectResponse(f"/courses/{course.id}", status_code=303)


@app.post("/courses/{course_id}/clarifications")
def answer_clarifications(
    course_id: int,
    request: Request,
    answers: list[str] = Form(...),
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    course = db.get(Course, course_id)
    if not course or course.user_id != user.id:
        raise HTTPException(status_code=404)

    answer_course_clarifications(db, course, answers)
    return RedirectResponse(f"/courses/{course.id}", status_code=303)


@app.post("/courses/{course_id}/delete")
def delete_course(course_id: int, request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    course = require_owned_course(db, user, course_id)
    db.delete(course)
    db.commit()
    return RedirectResponse("/", status_code=303)


@app.get("/courses/{course_id}/export.md", response_class=PlainTextResponse)
def export_course_markdown(
    course_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    course = require_owned_course(db, user, course_id)
    return PlainTextResponse(
        render_course_markdown(course),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="course-{course.id}.md"',
        },
    )


@app.get("/courses/{course_id}")
def show_course(course_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    course = db.get(Course, course_id)
    if not course or course.user_id != user.id:
        raise HTTPException(status_code=404)

    return templates.TemplateResponse(
        "course.html",
        {
            "request": request,
            "course": course,
            "progress": course_progress(course),
        },
    )


@app.get("/courses/{course_id}/modules/{module_id}")
def show_module(course_id: int, module_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    if not user:
        return RedirectResponse("/login", status_code=303)
    course = db.get(Course, course_id)
    module = db.get(Module, module_id)
    if not course or course.user_id != user.id or not module or module.course_id != course.id:
        raise HTTPException(status_code=404)
    if module.status == "locked":
        return RedirectResponse(f"/courses/{course.id}", status_code=303)

    module = ensure_module_content(db, course, module)

    attempts = db.scalars(
        select(Attempt)
        .where(Attempt.module_id == module.id, Attempt.user_id == course.user_id)
        .order_by(Attempt.created_at.asc())
    ).all()
    return templates.TemplateResponse(
        "module.html",
        {
            "request": request,
            "course": course,
            "module": module,
            "attempts": attempts,
        },
    )


@app.post("/courses/{course_id}/modules/{module_id}/attempts")
def submit_attempt(
    course_id: int,
    module_id: int,
    request: Request,
    answer: str = Form(...),
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    course = db.get(Course, course_id)
    module = db.get(Module, module_id)
    if not course or course.user_id != user.id or not module or module.course_id != course.id or not module.content:
        raise HTTPException(status_code=404)

    submit_module_attempt(db, course, module, answer)
    return RedirectResponse(f"/courses/{course.id}/modules/{module.id}", status_code=303)


@app.post("/courses/{course_id}/modules/{module_id}/continue")
def continue_after_explanation(
    course_id: int,
    module_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = require_user(request, db)
    course = db.get(Course, course_id)
    module = db.get(Module, module_id)
    if not course or course.user_id != user.id or not module or module.course_id != course.id:
        raise HTTPException(status_code=404)

    if not continue_after_explanation_service(db, course, module):
        return RedirectResponse(f"/courses/{course.id}/modules/{module.id}", status_code=303)
    return RedirectResponse(f"/courses/{course.id}", status_code=303)
