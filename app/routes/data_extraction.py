from flask import Blueprint, jsonify, request
from app.services.feature_engineering import FeatureEngineeringService
from app.models.app_data import AppLog
from app.extensions import db

# Definimos un Blueprint. Esto agrupa rutas relacionadas.
# url_prefix='/api/v1' significa que todas las rutas aquí empezarán con eso.
data_bp = Blueprint('data_extraction', __name__, url_prefix='/api/v1')

@data_bp.route('/client-features/<cod_cliente>', methods=['GET'])
def get_client_features(cod_cliente):
    """
    Endpoint para obtener el vector de características de un cliente.
    Uso: GET /api/v1/client-features/C00001
    """
    try:
        # Llamamos al servicio de lógica de negocio
        features = FeatureEngineeringService.get_client_features(cod_cliente)
        
        if not features:
            # Logueamos el intento fallido (opcional)
            log = AppLog(level='WARNING', message=f'Cliente no encontrado: {cod_cliente}', module='data_extraction')
            db.session.add(log)
            db.session.commit()
            
            return jsonify({'error': 'Cliente no encontrado'}), 404

        # Logueamos el acceso exitoso
        log = AppLog(level='INFO', message=f'Features extraidas para: {cod_cliente}', module='data_extraction')
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
