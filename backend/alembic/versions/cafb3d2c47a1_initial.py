"""initial

Revision ID: cafb3d2c47a1
Revises: 
Create Date: 2024-12-22 00:23:18.462257

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision: str = 'cafb3d2c47a1'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_items_barcode', table_name='items')
    op.drop_index('ix_items_category', table_name='items')
    op.drop_index('ix_items_location', table_name='items')
    op.drop_index('ix_items_name', table_name='items')
    op.drop_table('items')
    op.drop_table('backups')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_index('ix_users_username', table_name='users')
    op.drop_table('users')
    op.drop_table('item_images')
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('item_images',
    sa.Column('id', sa.VARCHAR(length=36), nullable=False),
    sa.Column('item_id', sa.VARCHAR(length=36), nullable=True),
    sa.Column('filename', sa.VARCHAR(), nullable=True),
    sa.Column('file_path', sa.VARCHAR(), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.ForeignKeyConstraint(['item_id'], ['items.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('id', sa.VARCHAR(length=36), nullable=False),
    sa.Column('email', sa.VARCHAR(), nullable=True),
    sa.Column('username', sa.VARCHAR(), nullable=True),
    sa.Column('hashed_password', sa.VARCHAR(), nullable=True),
    sa.Column('is_active', sa.BOOLEAN(), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_users_username', 'users', ['username'], unique=1)
    op.create_index('ix_users_email', 'users', ['email'], unique=1)
    op.create_table('backups',
    sa.Column('id', sa.VARCHAR(length=36), nullable=False),
    sa.Column('owner_id', sa.VARCHAR(length=36), nullable=True),
    sa.Column('filename', sa.VARCHAR(), nullable=True),
    sa.Column('file_path', sa.VARCHAR(), nullable=True),
    sa.Column('size_bytes', sa.INTEGER(), nullable=True),
    sa.Column('item_count', sa.INTEGER(), nullable=True),
    sa.Column('image_count', sa.INTEGER(), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.Column('status', sa.VARCHAR(), nullable=True),
    sa.Column('error_message', sa.VARCHAR(), nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('items',
    sa.Column('id', sa.VARCHAR(length=36), nullable=False),
    sa.Column('name', sa.VARCHAR(), nullable=True),
    sa.Column('category', sa.VARCHAR(), nullable=True),
    sa.Column('location', sa.VARCHAR(), nullable=True),
    sa.Column('brand', sa.VARCHAR(), nullable=True),
    sa.Column('model_number', sa.VARCHAR(), nullable=True),
    sa.Column('serial_number', sa.VARCHAR(), nullable=True),
    sa.Column('barcode', sa.VARCHAR(), nullable=True),
    sa.Column('purchase_date', sa.DATETIME(), nullable=True),
    sa.Column('purchase_price', sa.FLOAT(), nullable=True),
    sa.Column('current_value', sa.FLOAT(), nullable=True),
    sa.Column('warranty_expiration', sa.DATETIME(), nullable=True),
    sa.Column('notes', sa.VARCHAR(), nullable=True),
    sa.Column('custom_fields', sqlite.JSON(), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.Column('updated_at', sa.DATETIME(), nullable=True),
    sa.Column('owner_id', sa.VARCHAR(length=36), nullable=True),
    sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_items_name', 'items', ['name'], unique=False)
    op.create_index('ix_items_location', 'items', ['location'], unique=False)
    op.create_index('ix_items_category', 'items', ['category'], unique=False)
    op.create_index('ix_items_barcode', 'items', ['barcode'], unique=False)
    # ### end Alembic commands ###
