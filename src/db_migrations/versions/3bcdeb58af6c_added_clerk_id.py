"""Added clerk_id

Revision ID: 3bcdeb58af6c
Revises: 1f9ba987f39e
Create Date: 2025-04-03 18:25:04.283774

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '3bcdeb58af6c'
down_revision: Union[str, None] = '1f9ba987f39e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_tokenblacklist_token', table_name='tokenblacklist')
    op.drop_table('tokenblacklist')
    op.add_column('user', sa.Column('clerk_id', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.alter_column('user', 'id',
               existing_type=sa.INTEGER(),
               type_=sqlmodel.sql.sqltypes.AutoString(),
               existing_nullable=False)
    op.create_index(op.f('ix_user_clerk_id'), 'user', ['clerk_id'], unique=True)
    op.drop_column('user', 'uuid')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user', sa.Column('uuid', sa.VARCHAR(), autoincrement=False, nullable=False))
    op.drop_index(op.f('ix_user_clerk_id'), table_name='user')
    op.alter_column('user', 'id',
               existing_type=sqlmodel.sql.sqltypes.AutoString(),
               type_=sa.INTEGER(),
               existing_nullable=False)
    op.drop_column('user', 'clerk_id')
    op.create_table('tokenblacklist',
    sa.Column('id', sa.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('token', sa.VARCHAR(), autoincrement=False, nullable=False),
    sa.Column('expires_at', postgresql.TIMESTAMP(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', name='tokenblacklist_pkey')
    )
    op.create_index('ix_tokenblacklist_token', 'tokenblacklist', ['token'], unique=True)
    # ### end Alembic commands ###
