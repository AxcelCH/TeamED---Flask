from flask import Blueprint, request, jsonify
from app.models.app_data import ModelConfig, TrainedModel
from app.extensions import db
import datetime

models_bp = Blueprint('models', __name__, url_prefix='/api/v1/models')

@models_bp.route('/upload', methods=['POST'])
def upload_model():
    """
    Sube un modelo entrenado (.pkl) y lo guarda en la base de datos.
    ---
    tags:
      - Model Management
    consumes:
      - multipart/form-data
    parameters:
      - name: model_file
        in: formData
        type: file
        required: true
        description: Archivo binario del modelo (pickle/joblib)
      - name: version
        in: formData
        type: string
        required: true
        description: Versión del modelo (ej. v1.0.0)
      - name: parameters
        in: formData
        type: string
        description: JSON string con hiperparámetros (opcional)
    responses:
      201:
        description: Modelo guardado exitosamente
      400:
        description: Error en la petición
    """
    try:
        if 'model_file' not in request.files:
            return jsonify({'error': 'No se envió el archivo model_file'}), 400
        
        file = request.files['model_file']
        version = request.form.get('version')
        
        if not version:
            return jsonify({'error': 'La versión es obligatoria'}), 400

        # 1. Crear o buscar la configuración del modelo
        config = ModelConfig.query.filter_by(version=version).first()
        if not config:
            config = ModelConfig(
                version=version,
                parameters=request.form.get('parameters', {}),
                is_active=True
            )
            db.session.add(config)
            db.session.commit()

        # 2. Guardar el binario del modelo
        model_binary = file.read()
        new_model = TrainedModel(
            version=version,
            model_binary=model_binary
        )
        
        db.session.add(new_model)
        db.session.commit()

        return jsonify({'status': 'success', 'message': f'Modelo {version} guardado correctamente'}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
