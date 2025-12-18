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

    # Configuración de JWT
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'super-secret-jwt-key'
    JWT_ACCESS_TOKEN_EXPIRES = 3600 * 24 # 1 día de validez por defecto

    # Configuración de Mainframe (CICS / zOS Connect)
    MAINFRAME_CICS_URL = os.environ.get('MAINFRAME_CICS_URL')
    
    # Flag para usar simulación local en lugar de conectar al Mainframe real
    # Si es True, usa la BD local. Si es False, intenta conectar a MAINFRAME_CICS_URL.
    USE_MOCK_MAINFRAME = os.environ.get('USE_MOCK_MAINFRAME', 'True').lower() == 'true'

    # Aquí podrías agregar configuraciones para DB2 en el futuro
    # DB2_DATABASE_URI = os.environ.get('DB2_DATABASE_URI')
