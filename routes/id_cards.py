from flask import Blueprint, request, jsonify, send_file, current_app
from functools import wraps
from io import BytesIO
from datetime import datetime
import os

from models.employee import Employee
from models.site import Site
from routes.auth import token_required

# PDF generation
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


id_cards_bp = Blueprint("id_cards", __name__)


def require_admin_or_superadmin(f):
    @wraps(f)
    def decorated(current_user, *args, **kwargs):
        if not current_user or current_user.role not in ["admin", "superadmin"]:
            return jsonify({"success": False, "message": "Forbidden"}), 403
        return f(current_user, *args, **kwargs)
    return decorated


def _employee_to_preview(emp: Employee):
    site_name = emp.site.site_name if getattr(emp, "site", None) else None
    full_name = f"{emp.first_name} {emp.last_name}".strip()
    return {
        "id": emp.employee_id,
        "employee_id": str(emp.employee_id),
        "name": full_name,
        "designation": emp.designation or emp.job_title or "",
        "blood_group": emp.blood_group or None,
        "site": site_name,
    }


@id_cards_bp.route("/preview/<employee_id>", methods=["GET"])
@token_required
@require_admin_or_superadmin
def preview_single(current_user, employee_id):
    try:
        emp = Employee.query.filter_by(employee_id=employee_id).first()
        if not emp:
            return jsonify({"success": False, "message": "Employee not found"}), 404
        return jsonify({"success": True, "data": _employee_to_preview(emp)}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@id_cards_bp.route("/preview/bulk", methods=["GET"])
@token_required
@require_admin_or_superadmin
def preview_bulk(current_user):
    try:
        site_id = request.args.get("site_id")
        employee_ids = request.args.getlist("employee_ids[]") or request.args.getlist("employee_ids")

        print(f"DEBUG: site_id={site_id}, employee_ids={employee_ids}")

        query = Employee.query

        # Handle site filtering using salary codes (matching frontend logic)
        if site_id and site_id.strip():
            from models.site import Site
            from models.wage_master import WageMaster

            site = Site.query.filter_by(site_id=site_id).first()
            print(f"DEBUG: Site found: {site.site_name if site else 'None'}")

            if site:
                # Get all salary codes for this site
                site_salary_codes = WageMaster.query.filter_by(site_name=site.site_name).all()
                salary_code_list = [sc.salary_code for sc in site_salary_codes]
                print(f"DEBUG: Salary codes for site: {salary_code_list}")

                # Filter employees by salary codes
                if salary_code_list:
                    query = query.filter(Employee.salary_code.in_(salary_code_list))
                    print(f"DEBUG: Applied salary code filter: {salary_code_list}")
                else:
                    # No salary codes found for this site, return empty
                    print("DEBUG: No salary codes found for site, returning empty")
                    return jsonify({
                        "success": True,
                        "data": {
                            "count": 0,
                            "employees": []
                        }
                    }), 200
            else:
                # Site not found, return empty
                print("DEBUG: Site not found, returning empty")
                return jsonify({
                    "success": True,
                    "data": {
                        "count": 0,
                        "employees": []
                    }
                }), 200

        # Handle custom employee selection
        if employee_ids:
            query = query.filter(Employee.employee_id.in_(employee_ids))
            print(f"DEBUG: Filtering by employee_ids: {employee_ids}")

        employees = query.all()
        print(f"DEBUG: Found {len(employees)} employees")

        previews = [_employee_to_preview(e) for e in employees]
        print(f"DEBUG: Generated {len(previews)} previews")

        return jsonify({"success": True, "data": {"count": len(previews), "employees": previews}}), 200
    except Exception as e:
        print(f"DEBUG: Error in preview_bulk: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500


def _draw_logo(c, x, y, size_mm=12):
    logo_size = size_mm * mm

    # Hardcoded absolute path to the logo (most reliable approach)
    logo_path = r"E:\Projects\emp-management-system\employee-management\public\assets\SSPL.png"

    print(f"DEBUG: Using hardcoded logo path: {logo_path}")
    print(f"DEBUG: Logo file exists: {os.path.exists(logo_path)}")

    if os.path.exists(logo_path):
        try:
            # Try to open and validate the image first
            from PIL import Image
            img = Image.open(logo_path)
            print(f"DEBUG: PIL opened image successfully: {img.format}, size: {img.size}")

            # Now try ReportLab
            c.drawImage(
                logo_path,
                x,
                y,
                width=logo_size,
                height=logo_size,
                preserveAspectRatio=True,
                mask='auto',
            )
            print(f"DEBUG: Successfully loaded logo from: {logo_path}")
            return True
        except Exception as e:
            print(f"DEBUG: Failed to load logo from {logo_path}: {e}")
            import traceback
            traceback.print_exc()

    # Fallback: Draw SSPL text in white box
    print("DEBUG: No logo found, using text fallback")
    c.setFillColor(colors.white)
    c.rect(x, y, logo_size, logo_size, fill=1, stroke=1)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(colors.HexColor("#dc2626"))
    c.drawCentredString(x + logo_size / 2, y + logo_size / 2 - 2, "SSPL")
    return False


def _draw_card(c: canvas.Canvas, origin_x: float, origin_y: float, data: dict):
    """
    Draw a single ID card at position (origin_x, origin_y)
    Origin is at TOP-LEFT corner of the card
    """
    # Card dimensions (CR80 standard)
    card_w = 85.6 * mm
    card_h = 53.98 * mm

    # Convert top-left origin to bottom-left for PDF coordinate system
    bottom_x = origin_x
    bottom_y = origin_y - card_h

    # === CARD BORDER ===
    c.setStrokeColor(colors.HexColor("#1e40af"))
    c.setLineWidth(2)
    c.rect(bottom_x, bottom_y, card_w, card_h, stroke=1, fill=0)

    # === RED HEADER SECTION ===
    header_height = 15 * mm
    header_bottom_y = bottom_y + card_h - header_height

    c.setFillColor(colors.HexColor("#dc2626"))
    c.rect(bottom_x, header_bottom_y, card_w, header_height, fill=1, stroke=0)

    # Logo in header (top-left)
    logo_x = bottom_x + 3 * mm
    logo_y = header_bottom_y + 2 * mm
    _draw_logo(c, logo_x, logo_y, size_mm=11)

    # Company name (centered in header)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawCentredString(
        bottom_x + card_w / 2,
        header_bottom_y + header_height / 2 - 2,
        "SECURITECH SEVEN PVT LTD"
    )

    # === MAIN CONTENT AREA ===
    content_top = header_bottom_y - 2 * mm

    # Photo box (LEFT side) - 20mm x 25mm (matches preview)
    photo_x = bottom_x + 5 * mm
    photo_w = 20 * mm
    photo_h = 25 * mm
    photo_y = content_top - photo_h

    c.setFillColor(colors.HexColor("#f3f4f6"))
    c.setStrokeColor(colors.HexColor("#9ca3af"))
    c.setLineWidth(1)
    c.rect(photo_x, photo_y, photo_w, photo_h, fill=1, stroke=1)

    # "PHOTO" text centered in box
    c.setFillColor(colors.HexColor("#6b7280"))
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(photo_x + photo_w/2, photo_y + photo_h/2 - 2, "PHOTO")

    # Employee details (RIGHT of photo) - matches preview spacing
    details_x = photo_x + photo_w + 8 * mm
    details_y = content_top - 5 * mm
    line_spacing = 5.5 * mm

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 8)

    name = (data.get("name") or "")[:28]
    designation = (data.get("designation") or "")[:28]
    emp_id = str(data.get("employee_id") or "")
    blood = data.get("blood_group") or "____"

    c.drawString(details_x, details_y, f"Name: {name}")
    c.drawString(details_x, details_y - line_spacing, f"Rank: {designation}")
    c.drawString(details_x, details_y - 2*line_spacing, f"ID No: {emp_id}")
    c.drawString(details_x, details_y - 3*line_spacing, f"Blood Group: {blood}")

    # === BOTTOM SECTION (matches preview layout - compact spacing) ===
    # Position separator line 2mm below the photo box (matches preview)
    separator_y = photo_y - 2 * mm

    # Horizontal separator line
    c.setStrokeColor(colors.HexColor("#d1d5db"))
    c.setLineWidth(0.5)
    c.line(bottom_x + 2*mm, separator_y, bottom_x + card_w - 2*mm, separator_y)

    # Vertical divider (middle of card)
    divider_x = bottom_x + card_w / 2
    c.line(divider_x, bottom_y + 2*mm, divider_x, separator_y)

    # Set font for bottom section (smaller font to fit)
    c.setFont("Helvetica", 5.5)  # Reduced from 6 to 5.5
    c.setFillColor(colors.black)

    # === LEFT COLUMN (Below separator - tighter spacing) ===
    left_margin = bottom_x + 2 * mm  # Reduced margin

    # Start closer to separator (1.5mm instead of 3mm)
    y_offset = separator_y - 1.5 * mm

    # Date of Issue (compact)
    c.drawString(left_margin, y_offset, "Date of Issue:")
    c.line(left_margin + 16*mm, y_offset - 0.8*mm, divider_x - 2*mm, y_offset - 0.8*mm)

    # Signature of the Cardholder label (smaller spacing)
    y_offset -= 3.5 * mm  # Reduced from 5mm
    c.drawString(left_margin, y_offset, "Signature of the Cardholder:")

    # Signature line for cardholder
    y_offset -= 1.5 * mm  # Reduced from 2mm
    c.line(left_margin, y_offset, divider_x - 2*mm, y_offset)

    # Valid upto (smaller spacing)
    y_offset -= 3 * mm  # Reduced from 4mm
    c.drawString(left_margin, y_offset, "Valid upto:")
    c.line(left_margin + 12*mm, y_offset - 0.8*mm, divider_x - 2*mm, y_offset - 0.8*mm)

    # === RIGHT COLUMN (Below separator - tighter spacing) ===
    right_margin = divider_x + 2 * mm  # Reduced margin

    # Reset y_offset for right column
    y_offset = separator_y - 1.5 * mm

    # ID No (repeated)
    c.drawString(right_margin, y_offset, f"ID No: {emp_id}")

    # Signature of Issuing Authority label (smaller spacing)
    y_offset -= 3.5 * mm  # Reduced from 5mm
    c.drawString(right_margin, y_offset, "Signature of Issuing Authority")

    # Signature line for authority
    y_offset -= 1.5 * mm  # Reduced from 2mm
    c.line(right_margin, y_offset, bottom_x + card_w - 2*mm, y_offset)


def _generate_pdf(employees_data):
    """Generate PDF with ID cards (2 per A4 landscape page)"""
    buffer = BytesIO()
    page_w, page_h = landscape(A4)
    c = canvas.Canvas(buffer, pagesize=(page_w, page_h))

    # Card dimensions
    card_w = 85.6 * mm
    card_h = 53.98 * mm

    # Calculate positions to center cards on page
    # Horizontal: divide page into 2 columns with equal spacing
    total_card_width = 2 * card_w
    horizontal_spacing = (page_w - total_card_width) / 3  # 3 gaps (left, middle, right)

    # Vertical: center vertically on page
    vertical_margin = (page_h - card_h) / 2

    # Two card positions per page (top-left coordinates)
    positions = [
        (horizontal_spacing, vertical_margin + card_h),  # Left card (origin is top-left)
        (horizontal_spacing * 2 + card_w, vertical_margin + card_h),  # Right card
    ]

    for i, emp_data in enumerate(employees_data):
        pos_index = i % 2
        origin_x, origin_y = positions[pos_index]

        _draw_card(c, origin_x, origin_y, emp_data)

        # Start new page after every 2 cards
        if (i + 1) % 2 == 0 and i < len(employees_data) - 1:
            c.showPage()

    c.save()
    buffer.seek(0)
    return buffer


@id_cards_bp.route("/generate/individual", methods=["POST"])
@token_required
@require_admin_or_superadmin
def generate_individual(current_user):
    try:
        data = request.get_json() or {}
        employee_id = data.get("employee_id")
        if not employee_id:
            return jsonify({"success": False, "message": "employee_id is required"}), 400
        emp = Employee.query.filter_by(employee_id=employee_id).first()
        if not emp:
            return jsonify({"success": False, "message": "Employee not found"}), 404

        card_data = _employee_to_preview(emp)
        pdf_buffer = _generate_pdf([card_data])

        date_str = datetime.utcnow().strftime("%Y%m%d")
        filename = f"id_card_{card_data['employee_id']}_{date_str}.pdf"
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@id_cards_bp.route("/generate/bulk", methods=["POST"])
@token_required
@require_admin_or_superadmin
def generate_bulk(current_user):
    try:
        data = request.get_json() or {}
        mode = data.get("mode", "all")  # all | site | custom
        employee_ids = data.get("employee_ids") or []
        site_id = data.get("site_id")

        print(f"DEBUG: generate_bulk - mode={mode}, site_id={site_id}, employee_ids={employee_ids}")

        query = Employee.query

        # Handle site mode with salary code filtering
        if mode == "site" and site_id:
            from models.site import Site
            from models.wage_master import WageMaster

            site = Site.query.filter_by(site_id=site_id).first()
            print(f"DEBUG: Site found: {site.site_name if site else 'None'}")

            if site:
                # Get all salary codes for this site
                site_salary_codes = WageMaster.query.filter_by(site_name=site.site_name).all()
                salary_code_list = [sc.salary_code for sc in site_salary_codes]
                print(f"DEBUG: Salary codes for site: {salary_code_list}")

                # Filter employees by salary codes
                if salary_code_list:
                    query = query.filter(Employee.salary_code.in_(salary_code_list))
                    print(f"DEBUG: Applied salary code filter: {salary_code_list}")
                else:
                    return jsonify({
                        "success": False,
                        "message": "No employees found for this site"
                    }), 404
            else:
                return jsonify({
                    "success": False,
                    "message": "Site not found"
                }), 404
        elif mode == "custom" and employee_ids:
            query = query.filter(Employee.employee_id.in_(employee_ids))

        employees = query.all()
        print(f"DEBUG: Found {len(employees)} employees for PDF generation")

        if not employees:
            return jsonify({
                "success": False,
                "message": "No employees found for selection"
            }), 404

        cards = [_employee_to_preview(e) for e in employees]
        pdf_buffer = _generate_pdf(cards)

        date_str = datetime.utcnow().strftime("%Y%m%d")
        filename = f"id_cards_bulk_{len(cards)}_employees_{date_str}.pdf"
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=filename,
        )
    except Exception as e:
        print(f"Error in generate_bulk: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)}), 500



