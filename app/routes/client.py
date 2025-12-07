from flask import Blueprint, jsonify
from app.services.client_service import ClientService

client_bp = Blueprint('client', __name__, url_prefix='/api/v1/clients')

@client_bp.route('/<dni>/products', methods=['GET'])
def get_products(dni):
    """
    Obtiene los productos (cuentas y tarjetas) de un cliente.
    ---
    tags:
      - Client 360
    parameters:
      - name: dni
        in: path
        type: string
        required: true
        description: DNI del cliente
    responses:
      200:
        description: Lista de productos del cliente
      404:
        description: Cliente no encontrado
    """
    data = ClientService.get_products(dni)
    if not data:
        return jsonify({'error': 'Cliente no encontrado'}), 404
    return jsonify(data), 200

@client_bp.route('/<dni>/transactions', methods=['GET'])
def get_transactions(dni):
    """
    Obtiene el historial de transacciones de un cliente.
    ---
    tags:
      - Client 360
    parameters:
      - name: dni
        in: path
        type: string
        required: true
        description: DNI del cliente
    responses:
      200:
        description: Historial de transacciones
      404:
        description: Cliente no encontrado
    """
    data = ClientService.get_transactions(dni)
    if data is None: # Puede ser lista vacía [], así que chequeamos None
        return jsonify({'error': 'Cliente no encontrado'}), 404
    return jsonify({'transactions': data}), 200
