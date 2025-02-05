"""Add first_name, last_name, profile_picture to User model

Revision ID: ce68523124b5
Revises: 
Create Date: 2024-06-28 00:24:55.849411

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'ce68523124b5'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.add_column(sa.Column('first_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('last_name', sa.String(length=150), nullable=True))
        batch_op.add_column(sa.Column('profile_picture', sa.String(length=300), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('user', schema=None) as batch_op:
        batch_op.drop_column('profile_picture')
        batch_op.drop_column('last_name')
        batch_op.drop_column('first_name')

    # ### end Alembic commands ###
