"""init hrms schema

Revision ID: 20260225_000001
Revises:
Create Date: 2026-02-25 00:00:01

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260225_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


attendance_status = postgresql.ENUM("PRESENT", "ABSENT", name="attendance_status", create_type=False)


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.String(length=32), nullable=False),
        sa.Column("full_name", sa.String(length=150), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_employees_id"), "employees", ["id"], unique=False)
    op.create_index(op.f("ix_employees_employee_id"), "employees", ["employee_id"], unique=True)
    op.create_index(op.f("ix_employees_email"), "employees", ["email"], unique=True)

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'attendance_status') THEN
                CREATE TYPE attendance_status AS ENUM ('PRESENT', 'ABSENT');
            END IF;
        END$$;
        """
    )
    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("employee_id", sa.String(length=32), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", attendance_status, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.employee_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("employee_id", "date", name="uq_attendance_employee_date"),
    )
    op.create_index(op.f("ix_attendance_id"), "attendance", ["id"], unique=False)
    op.create_index(op.f("ix_attendance_employee_id"), "attendance", ["employee_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_attendance_employee_id"), table_name="attendance")
    op.drop_index(op.f("ix_attendance_id"), table_name="attendance")
    op.drop_table("attendance")
    op.execute("DROP TYPE IF EXISTS attendance_status")

    op.drop_index(op.f("ix_employees_email"), table_name="employees")
    op.drop_index(op.f("ix_employees_employee_id"), table_name="employees")
    op.drop_index(op.f("ix_employees_id"), table_name="employees")
    op.drop_table("employees")
