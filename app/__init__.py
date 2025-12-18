from flask import Flask
from app.config import Config
from app.extensions import db, jwt
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
    jwt.init_app(app)
    migrate.init_app(app, db)
    
    # Inicializar Swagger para documentación automática
    swagger = Swagger(app)

    # Configurar callback para verificar si un token está revocado (Logout)
    from app.models.mobile_app import TokenBlocklist
    
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        token = db.session.query(TokenBlocklist.id).filter_by(jti=jti).scalar()
        return token is not None

    # Registrar Blueprints (Rutas)
    from app.routes.auth import auth_bp
    from app.routes.products import products_bp
    from app.routes.coach import coach_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(coach_bp)

    # Crear tablas si no existen (Solo para desarrollo rápido, idealmente usar Flask-Migrate)
    with app.app_context():
        # Importar modelos para que SQLAlchemy los reconozca al crear tablas
        from app.models import core_banking, mobile_app
        db.create_all()

    return app
