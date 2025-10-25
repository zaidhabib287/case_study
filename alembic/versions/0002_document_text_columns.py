from alembic import op
import sqlalchemy as sa

revision = "0002_document_text_columns"
down_revision = "0001_init"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("documents") as batch:
        batch.add_column(sa.Column("content_text", sa.Text(), nullable=True))
        batch.add_column(sa.Column("content_preview", sa.String(length=400), nullable=True))

def downgrade():
    with op.batch_alter_table("documents") as batch:
        batch.drop_column("content_preview")
        batch.drop_column("content_text")
