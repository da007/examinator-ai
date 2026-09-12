"""add_exam_duration_minutes

Revision ID: a3f1c2d0e4b5
Revises: db192432ee13
Create Date: 2026-05-25 12:00:00.000000

FIX-6: добавляет поле exam_duration_minutes в таблицу lecture.
NULL означает «без ограничений по времени».
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = "a3f1c2d0e4b5"
down_revision: Union[str, None] = "db192432ee13"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "lecture",
        sa.Column("exam_duration_minutes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("lecture", "exam_duration_minutes")
