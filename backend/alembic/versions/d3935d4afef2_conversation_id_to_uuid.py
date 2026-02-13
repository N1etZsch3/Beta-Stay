"""conversation_id_to_uuid

Revision ID: d3935d4afef2
Revises: 1af1999c0b36
Create Date: 2026-02-14 01:37:29.433202

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d3935d4afef2"
down_revision: Union[str, Sequence[str], None] = "1af1999c0b36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: conversation.id and message.conversation_id from INTEGER to VARCHAR(36)."""
    # 1. Drop the foreign key constraint on message.conversation_id
    op.drop_constraint("message_conversation_id_fkey", "message", type_="foreignkey")

    # 2. Alter conversation.id: INTEGER -> VARCHAR(36), cast existing values to text
    op.alter_column(
        "conversation",
        "id",
        existing_type=sa.INTEGER(),
        type_=sa.String(length=36),
        existing_nullable=False,
        postgresql_using="id::text",
    )

    # 3. Alter message.conversation_id: INTEGER -> VARCHAR(36), cast existing values to text
    op.alter_column(
        "message",
        "conversation_id",
        existing_type=sa.INTEGER(),
        type_=sa.String(length=36),
        existing_nullable=False,
        postgresql_using="conversation_id::text",
    )

    # 4. Re-create the foreign key constraint
    op.create_foreign_key(
        "message_conversation_id_fkey",
        "message",
        "conversation",
        ["conversation_id"],
        ["id"],
    )


def downgrade() -> None:
    """Downgrade schema: revert to INTEGER."""
    op.drop_constraint("message_conversation_id_fkey", "message", type_="foreignkey")

    op.alter_column(
        "message",
        "conversation_id",
        existing_type=sa.String(length=36),
        type_=sa.INTEGER(),
        existing_nullable=False,
        postgresql_using="conversation_id::integer",
    )
    op.alter_column(
        "conversation",
        "id",
        existing_type=sa.String(length=36),
        type_=sa.INTEGER(),
        existing_nullable=False,
        postgresql_using="id::integer",
    )

    op.create_foreign_key(
        "message_conversation_id_fkey",
        "message",
        "conversation",
        ["conversation_id"],
        ["id"],
    )
