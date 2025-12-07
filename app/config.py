import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

class Config:
    """Configuración base de la aplicación."""
    
    # Clave secreta para seguridad de sesiones y cookies
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'una-clave-por-defecto-insegura'
    
    # URI de conexión a la base de datos principal (PostgreSQL)
    # Actualmente se usa para TODO (Core + App Data).
    # En el futuro, las tablas CORE_* se moverán a DB2.
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    
    # Configuración futura para Multi-DB (SQLAlchemy Binds)
    # SQLALCHEMY_BINDS = {
    #     'core': os.environ.get('DB2_DATABASE_URI')  # Para tablas del Mainframe
    # }
    
    # Desactivar el rastreo de modificaciones de objetos (ahorra memoria)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Aquí podrías agregar configuraciones para DB2 en el futuro
    # DB2_DATABASE_URI = os.environ.get('DB2_DATABASE_URI')
