"""add new table evaluator_history

Revision ID: 65718fcafdca
Revises: 04ce69254bbb
Create Date: 2024-10-31 04:54:54.459177+00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '65718fcafdca'
down_revision: Union[str, None] = '04ce69254bbb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evaluator_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('creator_id', sa.Integer(), nullable=True),
        sa.Column("data", sa.JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
     op.drop_table("evaluator_history")
