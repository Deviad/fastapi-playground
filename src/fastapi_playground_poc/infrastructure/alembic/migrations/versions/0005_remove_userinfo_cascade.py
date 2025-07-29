"""Remove CASCADE from userinfo foreign key

Revision ID: 0005
Revises: 0004
Create Date: 2025-07-21 01:32:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove ondelete CASCADE from userinfo foreign key constraint."""
    # Drop the existing foreign key constraint with CASCADE
    op.drop_constraint("user_info_user_id_fkey", "user_info", type_="foreignkey")

    # Recreate the foreign key constraint without ondelete CASCADE but keep onupdate CASCADE
    op.create_foreign_key(
        "user_info_user_id_fkey",
        "user_info",
        "users",
        ["user_id"],
        ["id"],
        onupdate="CASCADE",
    )


def downgrade() -> None:
    """Restore ondelete CASCADE to userinfo foreign key constraint."""
    # Drop the foreign key constraint without ondelete CASCADE
    op.drop_constraint("user_info_user_id_fkey", "user_info", type_="foreignkey")

    # Recreate the foreign key constraint with both ondelete and onupdate CASCADE
    op.create_foreign_key(
        "user_info_user_id_fkey",
        "user_info",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )
