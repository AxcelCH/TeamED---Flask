from app.extensions import db
from datetime import datetime

class AppLog(db.Model):
    """
    Tabla para guardar logs de la aplicación (ej. errores, accesos, ejecuciones del modelo).
    """
    __tablename__ = 'APP_LOGS'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(10), nullable=False) # INFO, ERROR, WARNING
    message = db.Column(db.Text, nullable=False)
    module = db.Column(db.String(50)) # Dónde ocurrió

class ModelConfig(db.Model):
    """
    Tabla para guardar configuraciones del modelo de clusterización.
    Ej: Hiperparámetros, fecha de entrenamiento, versión.
    """
    __tablename__ = 'MODEL_CONFIGS'

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(20), unique=True, nullable=False)
    parameters = db.Column(db.JSON) # Guardamos los parámetros como JSON (ej: {"n_clusters": 5})
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=False) # Cuál es la config activa actualmente

class TrainedModel(db.Model):
    """
    Tabla para guardar el binario del modelo entrenado (pickle/joblib).
    Nota: Para modelos muy grandes, es mejor usar almacenamiento de archivos (S3, disco),
    pero para prototipos o modelos ligeros, esto funciona.
    """
    __tablename__ = 'TRAINED_MODELS'

    id = db.Column(db.Integer, primary_key=True)
    version = db.Column(db.String(20), db.ForeignKey('MODEL_CONFIGS.version'), nullable=False)
    model_binary = db.Column(db.LargeBinary, nullable=False) # El archivo .pkl en bytes
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
