"""profilo di rischio per cliente

Revision ID: a7c1e2f4b9d0
Revises: d383c8047b66
Create Date: 2026-10-05 10:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7c1e2f4b9d0"
down_revision: str | Sequence[str] | None = "d383c8047b66"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("portfolios", sa.Column("risk_profile", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("portfolios", "risk_profile")
