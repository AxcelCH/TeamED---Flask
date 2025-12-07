from flask import Blueprint, jsonify
from app.services.analytics_service import AnalyticsService

analytics_bp = Blueprint('analytics', __name__, url_prefix='/api/v1/analytics')

@analytics_bp.route('/spending-category/<dni>', methods=['GET'])
def get_spending_category(dni):
    """
    Analiza los gastos del cliente por categoría.
    ---
    tags:
      - Analytics
    parameters:
      - name: dni
        in: path
        type: string
        required: true
        description: DNI del cliente
    responses:
      200:
        description: Gastos agrupados por categoría
      404:
        description: Cliente no encontrado
    """
    data = AnalyticsService.get_spending_by_category(dni)
    if not data:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    return jsonify(data), 200
