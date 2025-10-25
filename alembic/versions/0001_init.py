from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        "applications",
        sa.Column("application_id", sa.String(length=64), primary_key=True),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("age", sa.Integer(), nullable=False),
        sa.Column("address", sa.String(length=500), nullable=False),
        sa.Column("region_code", sa.String(length=16)),
        sa.Column("employment_status", sa.String(length=32), nullable=False, server_default="employed"),
        sa.Column("net_monthly_income", sa.Float()),
        sa.Column("credit_obligations_ratio", sa.Float()),
        sa.Column("dependents_under_12", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_table(
        "documents",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("application_id", sa.String(length=64), sa.ForeignKey("applications.application_id", ondelete="CASCADE"), index=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=128)),
        sa.Column("size_bytes", sa.Integer()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )
    op.create_table(
        "decisions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("application_id", sa.String(length=64), sa.ForeignKey("applications.application_id", ondelete="CASCADE"), index=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("eligibility_label", sa.String(length=32), nullable=False),
        sa.Column("probability", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("NOW()")),
    )

def downgrade():
    op.drop_table("decisions")
    op.drop_table("documents")
    op.drop_table("applications")
