"""universi di riferimento: benchmark per cliente, storico e composizione degli indici

Revision ID: c4e8b2d6f1a3
Revises: a7c1e2f4b9d0
Create Date: 2026-10-07 10:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c4e8b2d6f1a3"
down_revision: str | Sequence[str] | None = "a7c1e2f4b9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # NULL = benchmark predefinito (data/benchmarks.py): i clienti esistenti non cambiano
    op.add_column("portfolios", sa.Column("benchmark", sa.String(), nullable=True))
    op.create_table(
        "benchmark_prices",
        sa.Column("date", sa.String(), nullable=False),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("date", "ticker"),
    )
    op.create_table(
        "benchmark_constituents",
        sa.Column("benchmark", sa.String(), nullable=False),
        sa.Column("ticker", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("as_of", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("benchmark", "ticker"),
    )


def downgrade() -> None:
    op.drop_table("benchmark_constituents")
    op.drop_table("benchmark_prices")
    op.drop_column("portfolios", "benchmark")
