"""update_userinfo_foreign_key_cascade

Revision ID: 0003
Revises: 0002
Create Date: 2025-07-20 11:43:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing foreign key constraint
    op.drop_constraint("user_info_user_id_fkey", "user_info", type_="foreignkey")

    # Recreate the foreign key constraint with CASCADE delete
    op.create_foreign_key(
        "user_info_user_id_fkey",
        "user_info",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )


def downgrade() -> None:
    # Drop the CASCADE foreign key constraint
    op.drop_constraint("user_info_user_id_fkey", "user_info", type_="foreignkey")

    # Recreate the original foreign key constraint without CASCADE
    op.create_foreign_key(
        "user_info_user_id_fkey", "user_info", "users", ["user_id"], ["id"]
    )
