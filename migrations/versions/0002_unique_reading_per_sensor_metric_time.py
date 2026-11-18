"""make (sensor_id, metric, recorded_at) unique

Replaces the plain index with a unique one on the same columns. Fails if the database
already holds duplicate readings; remove them before upgrading.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

COLUMNS = ["sensor_id", "metric", "recorded_at"]


def upgrade() -> None:
    op.drop_index("ix_readings_sensor_metric_time", table_name="readings")
    op.create_index("ux_readings_sensor_metric_time", "readings", COLUMNS, unique=True)


def downgrade() -> None:
    op.drop_index("ux_readings_sensor_metric_time", table_name="readings")
    op.create_index("ix_readings_sensor_metric_time", "readings", COLUMNS)
