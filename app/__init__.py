from flask import Flask
from app.config import Config
from app.extensions import db
from flask_migrate import Migrate
from flasgger import Swagger

# Inicializamos Migrate globalmente
migrate = Migrate()

def create_app(config_class=Config):
    """
    Factory function para crear la aplicación Flask.
    Permite crear múltiples instancias con diferentes configuraciones (ej. testing).
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inicializar extensiones con la app
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Inicializar Swagger para documentación automática
    swagger = Swagger(app)

    # Registrar Blueprints (Rutas)
    from app.routes.data_extraction import data_bp
    app.register_blueprint(data_bp)

    # Crear tablas si no existen (Solo para desarrollo rápido, idealmente usar Flask-Migrate)
    with app.app_context():
        # Importar modelos para que SQLAlchemy los reconozca al crear tablas
        from app.models import core_banking, app_data
        db.create_all()

    return app
