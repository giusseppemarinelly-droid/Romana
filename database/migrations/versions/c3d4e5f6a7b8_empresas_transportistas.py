"""empresas transportistas

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('empresas_transportistas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(length=20), nullable=False),
        sa.Column('nombre', sa.String(length=100), nullable=False),
        sa.Column('rif', sa.String(length=20), nullable=True),
        sa.Column('direccion', sa.Text(), nullable=True),
        sa.Column('telefono', sa.String(length=20), nullable=True),
        sa.Column('email', sa.String(length=100), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('codigo')
    )
    op.create_index(op.f('ix_empresas_transportistas_id'), 'empresas_transportistas', ['id'], unique=False)

    op.add_column('pesadas', sa.Column('empresa_transportista_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_pesadas_empresa_transportista_id', 'pesadas',
        'empresas_transportistas', ['empresa_transportista_id'], ['id'],
    )


def downgrade() -> None:
    op.drop_constraint('fk_pesadas_empresa_transportista_id', 'pesadas', type_='foreignkey')
    op.drop_column('pesadas', 'empresa_transportista_id')
    op.drop_index(op.f('ix_empresas_transportistas_id'), table_name='empresas_transportistas')
    op.drop_table('empresas_transportistas')
