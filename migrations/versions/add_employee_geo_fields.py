"""Add employee geofence check-in fields

Revision ID: 20260622_add_employee_geo_checkin_fields
Revises: 20260602_add_wagemaster_site_id
Create Date: 2026-06-22 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'add_employee_geo_fields'
down_revision = '20260602_add_wagemaster_site_id'
branch_labels = None
depends_on = None


def _existing_columns(table_name: str) -> set[str]:
    connection = op.get_bind()
    return {column['name'] for column in inspect(connection).get_columns(table_name)}


def upgrade():
    site_columns = _existing_columns('sites')
    attendance_columns = _existing_columns('attendance')
    user_columns = _existing_columns('users')

    with op.batch_alter_table('sites', schema=None) as batch_op:
        if 'latitude' not in site_columns:
            batch_op.add_column(sa.Column('latitude', sa.Float(), nullable=True))
        if 'longitude' not in site_columns:
            batch_op.add_column(sa.Column('longitude', sa.Float(), nullable=True))
        if 'radius_metres' not in site_columns:
            batch_op.add_column(sa.Column('radius_metres', sa.Integer(), nullable=True, server_default=sa.text('200')))

    with op.batch_alter_table('attendance', schema=None) as batch_op:
        if 'selfie_photo_url' not in attendance_columns:
            batch_op.add_column(sa.Column('selfie_photo_url', sa.String(length=500), nullable=True))
        if 'check_in_latitude' not in attendance_columns:
            batch_op.add_column(sa.Column('check_in_latitude', sa.Float(), nullable=True))
        if 'check_in_longitude' not in attendance_columns:
            batch_op.add_column(sa.Column('check_in_longitude', sa.Float(), nullable=True))
        if 'gps_accuracy_metres' not in attendance_columns:
            batch_op.add_column(sa.Column('gps_accuracy_metres', sa.Float(), nullable=True))
        if 'is_within_geofence' not in attendance_columns:
            batch_op.add_column(sa.Column('is_within_geofence', sa.Boolean(), nullable=True))
        if 'attendance_source' not in attendance_columns:
            batch_op.add_column(sa.Column('attendance_source', sa.String(length=20), nullable=True, server_default='admin'))
        if 'fraud_flags' not in attendance_columns:
            batch_op.add_column(sa.Column('fraud_flags', sa.JSON(), nullable=True))
        if 'verification_status' not in attendance_columns:
            batch_op.add_column(sa.Column('verification_status', sa.String(length=20), nullable=True, server_default='auto_approved'))

    with op.batch_alter_table('users', schema=None) as batch_op:
        if 'device_id' not in user_columns:
            batch_op.add_column(sa.Column('device_id', sa.String(length=200), nullable=True))
        if 'is_temp_password' not in user_columns:
            batch_op.add_column(sa.Column('is_temp_password', sa.Boolean(), nullable=False, server_default=sa.text('true')))


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_temp_password')
        batch_op.drop_column('device_id')

    with op.batch_alter_table('attendance', schema=None) as batch_op:
        batch_op.drop_column('verification_status')
        batch_op.drop_column('fraud_flags')
        batch_op.drop_column('attendance_source')
        batch_op.drop_column('is_within_geofence')
        batch_op.drop_column('gps_accuracy_metres')
        batch_op.drop_column('check_in_longitude')
        batch_op.drop_column('check_in_latitude')
        batch_op.drop_column('selfie_photo_url')

    with op.batch_alter_table('sites', schema=None) as batch_op:
        batch_op.drop_column('radius_metres')
        batch_op.drop_column('longitude')
        batch_op.drop_column('latitude')