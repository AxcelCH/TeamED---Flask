from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager

# Inicializamos la instancia de SQLAlchemy
# Se usará en los modelos y en la creación de la app
db = SQLAlchemy()
jwt = JWTManager()
