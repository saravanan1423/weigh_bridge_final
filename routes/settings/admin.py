from flask import jsonify, render_template, request

from . import settings_bp
from admin_config import (
    RESET_SERIAL_DAILY_KEY,
    RESEND_BUTTON_ENABLED_KEY,
    LIVE_WEIGHT_ENABLED_KEY,
    UPDATE_MANIFEST_URL_KEY,
    ensure_admin_settings_schema,
    get_live_weight_enabled,
    get_rfid_enabled,
    get_reset_serial_daily,
    get_resend_button_enabled,
    get_tare_weight_enabled,
    get_update_manifest_url,
    set_admin_setting_bool,
    set_admin_setting_value,
)
from app_version import APP_VERSION
from auto_updater import apply_update_and_restart, check_for_update


@settings_bp.route("/admin")
def admin():
    ensure_admin_settings_schema()
    return render_template("admin_settings.html")


@settings_bp.route("/api/admin", methods=["GET"])
def admin_settings_details():
    return jsonify({
        "settings": {
            "resetSerialDaily": get_reset_serial_daily(),
            "rfidEnabled": get_rfid_enabled(),
            "tareWeightEnabled": get_tare_weight_enabled(),
            "resendButtonEnabled": get_resend_button_enabled(),
            "liveWeightEnabled": get_live_weight_enabled(),
            "updateManifestUrl": get_update_manifest_url(),
            "appVersion": APP_VERSION,
        }
    })


@settings_bp.route("/api/admin", methods=["POST"])
def admin_settings_save():
    payload = request.get_json(silent=True) or {}
    reset_serial_daily = bool(payload.get("resetSerialDaily"))
    resend_button_enabled = payload.get("resendButtonEnabled") is not False
    live_weight_enabled = payload.get("liveWeightEnabled") is not False
    update_manifest_url = str(payload.get("updateManifestUrl") or "").strip()
    rfid_enabled = get_rfid_enabled()
    tare_weight_enabled = get_tare_weight_enabled()
    set_admin_setting_bool(RESET_SERIAL_DAILY_KEY, reset_serial_daily)
    set_admin_setting_bool(RESEND_BUTTON_ENABLED_KEY, resend_button_enabled)
    set_admin_setting_bool(LIVE_WEIGHT_ENABLED_KEY, live_weight_enabled)
    set_admin_setting_value(UPDATE_MANIFEST_URL_KEY, update_manifest_url)
    return jsonify({
        "message": "Admin settings saved",
        "settings": {
            "resetSerialDaily": reset_serial_daily,
            "rfidEnabled": rfid_enabled,
            "tareWeightEnabled": tare_weight_enabled,
            "resendButtonEnabled": resend_button_enabled,
            "liveWeightEnabled": live_weight_enabled,
            "updateManifestUrl": update_manifest_url,
            "appVersion": APP_VERSION,
        },
    })


@settings_bp.route("/api/admin/update/check", methods=["GET"])
def admin_update_check():
    update_info = check_for_update(get_update_manifest_url())
    return jsonify(update_info)


@settings_bp.route("/api/admin/update/apply", methods=["POST"])
def admin_update_apply():
    update_info = check_for_update(get_update_manifest_url())
    if not update_info.get("updateAvailable"):
        return jsonify(update_info), 400
    try:
        apply_update_and_restart(update_info)
    except Exception as exc:
        return jsonify({"message": str(exc), **update_info}), 500
    return jsonify({
        **update_info,
        "message": "Update downloaded. The app will restart now.",
        "restarting": True,
    })
