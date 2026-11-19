"""agregar ruta de imagen a aportaciones

Revision ID: f3c1d2a7b9e4
Revises: e8a4f10869e4
Create Date: 2026-11-18 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3c1d2a7b9e4'
down_revision: Union[str, Sequence[str], None] = 'e8a4f10869e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('aportaciones', sa.Column('ruta_imagen', sa.String(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('aportaciones', 'ruta_imagen')
