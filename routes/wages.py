from flask import Blueprint, request, jsonify
from services.wage_master_service import generate_salary_code

wages_bp = Blueprint('wages', __name__)

@wages_bp.route("/generate-salary-code", methods=["POST"])
def create_salary_code():
    data = request.json
    code = generate_salary_code(data['site'], data['rank'], data['state'], set())
    return jsonify({"salaryCode": code})
