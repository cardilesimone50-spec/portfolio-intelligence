"""benchmark total return: i clienti sugli indici di prezzo passano alla serie TR

Revision ID: e7a3c9b1d5f2
Revises: c4e8b2d6f1a3
Create Date: 2026-10-07 16:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e7a3c9b1d5f2"
down_revision: str | Sequence[str] | None = "c4e8b2d6f1a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# indice di prezzo → serie total return dello stesso indice (data/benchmarks.py)
_TOTAL_RETURN = {"^GSPC": "^SP500TR", "FTSEMIB.MI": "CSMIB.MI", "^STOXX": "MEUD.PA"}


def _remap(mapping: dict[str, str]) -> None:
    conn = op.get_bind()
    for old, new in mapping.items():
        conn.execute(
            sa.text("UPDATE portfolios SET benchmark = :new WHERE benchmark = :old"),
            {"old": old, "new": new},
        )
        # lo storico salvato del vecchio indice non serve più: l'ingestion scarica il nuovo
        conn.execute(sa.text("DELETE FROM benchmark_prices WHERE ticker = :old"), {"old": old})


def upgrade() -> None:
    _remap(_TOTAL_RETURN)


def downgrade() -> None:
    _remap({new: old for old, new in _TOTAL_RETURN.items()})
