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
_TOTAL_RETURN = {"^GSPC": "SPY", "FTSEMIB.MI": "CSMIB.MI", "^STOXX": "EXSA.DE"}


def _remap(mapping: dict[str, str]) -> None:
    # op.execute con bindparams: valori resi anche in modalità offline (alembic --sql)
    for old, new in mapping.items():
        op.execute(
            sa.text("UPDATE portfolios SET benchmark = :new WHERE benchmark = :old").bindparams(
                old=old, new=new
            )
        )
        # lo storico salvato del vecchio indice non serve più: l'ingestion scarica il nuovo
        op.execute(sa.text("DELETE FROM benchmark_prices WHERE ticker = :old").bindparams(old=old))


def upgrade() -> None:
    _remap(_TOTAL_RETURN)


def downgrade() -> None:
    _remap({new: old for old, new in _TOTAL_RETURN.items()})
