"""add_phone_and_bio

Revision ID: db192432ee13
Revises: 4ef6b1a41817
Create Date: 2026-05-22 13:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'db192432ee13'
down_revision: Union[str, None] = '4ef6b1a41817'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user', sa.Column('phone', sa.String(length=255), nullable=True, comment='Номер телефона'))
    op.add_column('user', sa.Column('bio', sa.Text(), nullable=True, comment='О себе / Регалии'))


def downgrade() -> None:
    op.drop_column('user', 'bio')
    op.drop_column('user', 'phone')