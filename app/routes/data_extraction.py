from flask import Blueprint, jsonify, request
from app.services.feature_engineering import FeatureEngineeringService
from app.models.app_data import AppLog
from app.extensions import db

# Definimos un Blueprint. Esto agrupa rutas relacionadas.
# url_prefix='/api/v1' significa que todas las rutas aquí empezarán con eso.
data_bp = Blueprint('data_extraction', __name__, url_prefix='/api/v1')

@data_bp.route('/client-features/<dni>', methods=['GET'])
def get_client_features(dni):
    """
    Endpoint para obtener el vector de características de un cliente.
    ---
    tags:
      - Feature Engineering
    parameters:
      - name: dni
        in: path
        type: string
        required: true
        description: DNI o RUC del cliente
    responses:
      200:
        description: Vector de características calculado exitosamente
        schema:
          type: object
          properties:
            status:
              type: string
              example: success
            data:
              type: object
              properties:
                cod_cliente:
                  type: string
                edad:
                  type: integer
                ingresos_mes:
                  type: number
                score_crediticio:
                  type: integer
                total_saldo_cuentas:
                  type: number
                num_cuentas_activas:
                  type: integer
                num_tarjetas_credito:
                  type: integer
                total_monto_movimientos:
                  type: number
                promedio_monto_movimientos:
                  type: number
                num_transacciones:
                  type: integer
      404:
        description: Cliente no encontrado
      500:
        description: Error interno del servidor
    """
    try:
        # Llamamos al servicio de lógica de negocio
        features = FeatureEngineeringService.get_client_features(dni)
        
        if not features:
            # Logueamos el intento fallido (opcional)
            log = AppLog(level='WARNING', message=f'Cliente no encontrado por DNI: {dni}', module='data_extraction')
            db.session.add(log)
            db.session.commit()
            
            return jsonify({'error': 'Cliente no encontrado'}), 404

        # Logueamos el acceso exitoso
        log = AppLog(level='INFO', message=f'Features extraidas para DNI: {dni}', module='data_extraction')
        db.session.add(log)
        db.session.commit()

        return jsonify({
            'status': 'success',
            'data': features
        }), 200

    except Exception as e:
        # Captura de errores generales
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@data_bp.route('/training-data', methods=['GET'])
def get_training_data():
    """
    Obtiene un dataset completo (lista de clientes) para entrenar modelos.
    ---
    tags:
      - Feature Engineering
    parameters:
      - name: limit
        in: query
        type: integer
        default: 1000
        description: Cantidad máxima de registros a retornar
    responses:
      200:
        description: Dataset JSON listo para Pandas/Colab
    """
    try:
        limit = request.args.get('limit', default=1000, type=int)
        dataset = FeatureEngineeringService.get_training_dataset(limit=limit)
        
        return jsonify({
            'status': 'success',
            'count': len(dataset),
            'data': dataset
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
