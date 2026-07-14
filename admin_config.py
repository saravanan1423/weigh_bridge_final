from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import text

from models.models import db


ADMIN_SETTINGS_TABLE = "admin_settings"
RESET_SERIAL_DAILY_KEY = "reset_serial_daily"
RFID_ENABLED_KEY = "rfid_enabled"
TARE_WEIGHT_ENABLED_KEY = "tare_weight_enabled"
RESEND_BUTTON_ENABLED_KEY = "resend_button_enabled"
LIVE_WEIGHT_ENABLED_KEY = "live_weight_enabled"
UPDATE_MANIFEST_URL_KEY = "update_manifest_url"
BACKUP_ENABLED_KEY = "backup_enabled"
BACKUP_INTERVAL_MINUTES_KEY = "backup_interval_minutes"
BACKUP_TARGET_DIR_KEY = "backup_target_dir"
BACKUP_LAST_RUN_AT_KEY = "backup_last_run_at"


def ensure_admin_settings_schema():
    db.session.execute(
        text(
            f"""
            CREATE TABLE IF NOT EXISTS {ADMIN_SETTINGS_TABLE} (
                setting_key VARCHAR(80) PRIMARY KEY,
                setting_value VARCHAR(80) NOT NULL,
                updated_at DATETIME
            )
            """
        )
    )
    db.session.commit()


def get_admin_setting_bool(setting_key, default=False):
    ensure_admin_settings_schema()
    value = db.session.execute(
        text(f"SELECT setting_value FROM {ADMIN_SETTINGS_TABLE} WHERE setting_key = :setting_key"),
        {"setting_key": setting_key},
    ).scalar()
    if value is None:
        return bool(default)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def set_admin_setting_bool(setting_key, value):
    set_admin_setting_value(setting_key, "true" if value else "false")


def get_admin_setting_value(setting_key, default=""):
    ensure_admin_settings_schema()
    value = db.session.execute(
        text(f"SELECT setting_value FROM {ADMIN_SETTINGS_TABLE} WHERE setting_key = :setting_key"),
        {"setting_key": setting_key},
    ).scalar()
    if value is None:
        return default
    return str(value)


def set_admin_setting_value(setting_key, value):
    ensure_admin_settings_schema()
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    db.session.execute(
        text(
            f"""
            INSERT INTO {ADMIN_SETTINGS_TABLE} (setting_key, setting_value, updated_at)
            VALUES (:setting_key, :setting_value, :updated_at)
            ON CONFLICT(setting_key) DO UPDATE SET
                setting_value = excluded.setting_value,
                updated_at = excluded.updated_at
            """
        ),
        {
            "setting_key": setting_key,
            "setting_value": str(value),
            "updated_at": now,
        },
    )
    db.session.commit()


def get_admin_setting_int(setting_key, default=0, minimum=None, maximum=None):
    raw_value = get_admin_setting_value(setting_key, str(default))
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        value = int(default)
    if minimum is not None:
        value = max(int(minimum), value)
    if maximum is not None:
        value = min(int(maximum), value)
    return value


def get_reset_serial_daily():
    return get_admin_setting_bool(RESET_SERIAL_DAILY_KEY, True)


def get_rfid_enabled():
    return get_admin_setting_bool(RFID_ENABLED_KEY, True)


def get_tare_weight_enabled():
    return get_admin_setting_bool(TARE_WEIGHT_ENABLED_KEY, True)


def get_resend_button_enabled():
    return get_admin_setting_bool(RESEND_BUTTON_ENABLED_KEY, True)


def get_live_weight_enabled():
    return get_admin_setting_bool(LIVE_WEIGHT_ENABLED_KEY, True)


def get_update_manifest_url():
    return get_admin_setting_value(UPDATE_MANIFEST_URL_KEY, "")
