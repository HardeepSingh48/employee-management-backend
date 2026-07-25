from __future__ import annotations

import os

from flask import Blueprint, current_app, jsonify, send_file

from config import ATTENDANCE_UPLOADS_DIR
from routes.auth import token_required


media_bp = Blueprint("media", __name__)


@media_bp.route("/attendance/<int:employee_id>/<path:filename>", methods=["GET"])
@token_required
def get_attendance_photo(current_user, employee_id: int, filename: str):
    """Serve an attendance selfie if the requester owns the record or is an admin."""
    try:
        if current_user.role not in ["admin", "admin1", "admin2", "superadmin"] and current_user.employee_id != employee_id:
            return jsonify({"success": False, "message": "Unauthorized"}), 403

        file_path = os.path.join(ATTENDANCE_UPLOADS_DIR, str(employee_id), filename)
        if not os.path.isfile(file_path):
            return jsonify({"success": False, "message": "File not found"}), 404

        return send_file(file_path)
    except Exception as exc:
        current_app.logger.exception("Failed to serve attendance photo")
        return jsonify({"success": False, "message": f"Error serving file: {exc}"}), 500