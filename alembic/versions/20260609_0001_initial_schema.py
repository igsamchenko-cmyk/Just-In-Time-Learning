"""Initial schema.

Revision ID: 20260609_0001
Revises: None
Create Date: 2026-06-09
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260609_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("google_id", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("google_id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_id"), "users", ["id"], unique=False)

    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("original_request", sa.Text(), nullable=False),
        sa.Column("user_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("safety_status", sa.String(length=50), nullable=False),
        sa.Column("current_module_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_courses_id"), "courses", ["id"], unique=False)

    op.create_table(
        "course_clarifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_course_clarifications_id"),
        "course_clarifications",
        ["id"],
        unique=False,
    )

    op.create_table(
        "modules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("short_description", sa.Text(), nullable=False),
        sa.Column("learning_goal", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_modules_id"), "modules", ["id"], unique=False)

    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("hint", sa.Text(), nullable=True),
        sa.Column("explanation", sa.Text(), nullable=True),
        sa.Column("next_action", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attempts_id"), "attempts", ["id"], unique=False)

    op.create_table(
        "module_contents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("example", sa.Text(), nullable=False),
        sa.Column("task_type", sa.String(length=50), nullable=False),
        sa.Column("practical_task", sa.Text(), nullable=False),
        sa.Column("correct_answer_criteria", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("module_id"),
    )
    op.create_index(op.f("ix_module_contents_id"), "module_contents", ["id"], unique=False)

    op.create_table(
        "ai_requests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("course_id", sa.Integer(), nullable=True),
        sa.Column("module_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("request_type", sa.String(length=100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_requests_id"), "ai_requests", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_requests_id"), table_name="ai_requests")
    op.drop_table("ai_requests")
    op.drop_index(op.f("ix_module_contents_id"), table_name="module_contents")
    op.drop_table("module_contents")
    op.drop_index(op.f("ix_attempts_id"), table_name="attempts")
    op.drop_table("attempts")
    op.drop_index(op.f("ix_modules_id"), table_name="modules")
    op.drop_table("modules")
    op.drop_index(op.f("ix_course_clarifications_id"), table_name="course_clarifications")
    op.drop_table("course_clarifications")
    op.drop_index(op.f("ix_courses_id"), table_name="courses")
    op.drop_table("courses")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
