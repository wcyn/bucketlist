"""bucketlist_id

Revision ID: 9d18c039a538
Revises: 73ea12e8a3d0
Create Date: 2017-05-06 15:27:22.866584

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9d18c039a538'
down_revision = '73ea12e8a3d0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('bucketlist_item', sa.Column('bucketlist', sa.Integer(), nullable=False))
    op.drop_constraint('bucketlist_item_bucketlist_id_fkey', 'bucketlist_item', type_='foreignkey')
    op.create_foreign_key(None, 'bucketlist_item', 'bucketlist', ['bucketlist'], ['id'])
    op.drop_column('bucketlist_item', 'bucketlist_id')
    op.add_column('user_token', sa.Column('user_id', sa.Integer(), nullable=False))
    op.drop_constraint('user_token_user_key', 'user_token', type_='unique')
    op.create_unique_constraint(None, 'user_token', ['user_id'])
    op.drop_constraint('user_token_user_fkey', 'user_token', type_='foreignkey')
    op.create_foreign_key(None, 'user_token', 'user', ['user_id'], ['id'])
    op.drop_column('user_token', 'user')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user_token', sa.Column('user', sa.INTEGER(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'user_token', type_='foreignkey')
    op.create_foreign_key('user_token_user_fkey', 'user_token', 'user', ['user'], ['id'])
    op.drop_constraint(None, 'user_token', type_='unique')
    op.create_unique_constraint('user_token_user_key', 'user_token', ['user'])
    op.drop_column('user_token', 'user_id')
    op.add_column('bucketlist_item', sa.Column('bucketlist_id', sa.INTEGER(), autoincrement=False, nullable=False))
    op.drop_constraint(None, 'bucketlist_item', type_='foreignkey')
    op.create_foreign_key('bucketlist_item_bucketlist_id_fkey', 'bucketlist_item', 'bucketlist', ['bucketlist_id'], ['id'])
    op.drop_column('bucketlist_item', 'bucketlist')
    # ### end Alembic commands ###