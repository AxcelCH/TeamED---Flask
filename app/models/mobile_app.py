from app.extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class TokenBlocklist(db.Model):
    """
    Tabla para revocar tokens JWT (Logout).
    """
    __tablename__ = 'TOKEN_BLOCKLIST'
    
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True, comment='ID único del token (JWT ID)')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

class GamificacionAnimal(db.Model):
    __tablename__ = 'GAMIFICACION_ANIMALES'

    nivel_id = db.Column('NIVEL_ID', db.Integer, primary_key=True, comment='Ej: 1, 2, 3...')
    nombre_animal = db.Column('NOMBRE_ANIMAL', db.String(20), comment='Ej: Perezoso, Hormiga, Águila')
    descripcion_perfil = db.Column('DESCRIPCION_PERFIL', db.String(255), comment="Ej: 'Aún te cuesta mover tus ahorros...'")
    url_icono = db.Column('URL_ICONO', db.String(255))
    rango_gasto_min = db.Column('RANGO_GASTO_MIN', db.Numeric(15, 2), comment='Lógica para asignar este animal')
    rango_gasto_max = db.Column('RANGO_GASTO_MAX', db.Numeric(15, 2))

    # Relación inversa
    usuarios = db.relationship('Usuario', backref='gamificacion_perfil', lazy=True)

class Usuario(db.Model):
    __tablename__ = 'USUARIOS'

    user_uuid = db.Column('USER_UUID', db.String(50), primary_key=True, comment='ID único del sistema de Auth (Firebase/Cognito)')
    dni_vinculado = db.Column('DNI_VINCULADO', db.String(11), unique=True, nullable=False, comment='Llave para buscar datos en Mainframe')
    password_hash = db.Column('PASSWORD_HASH', db.String(255), comment='Hash de la contraseña para auth local')
    nickname = db.Column('NICKNAME', db.String(30))
    foto_perfil_url = db.Column('FOTO_PERFIL_URL', db.String(255))
    nivel_financiero = db.Column('NIVEL_FINANCIERO', db.Integer, db.ForeignKey('GAMIFICACION_ANIMALES.NIVEL_ID'), default=1, comment='Nivel actual del usuario')
    animal_actual = db.Column('ANIMAL_ACTUAL', db.String(20), default='Perezoso', comment='Nombre del arquetipo actual')
    created_at = db.Column('CREATED_AT', db.DateTime, default=datetime.utcnow)

    # Relaciones
    metas = db.relationship('Meta', backref='usuario', lazy=True)
    gastos_manuales = db.relationship('GastoManual', backref='usuario', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    presupuestos = db.relationship('Presupuesto', backref='usuario', lazy=True)
    desgloses = db.relationship('DesgloseMovimiento', backref='usuario', lazy=True)

class CategoriaConfig(db.Model):
    __tablename__ = 'CATEGORIAS_CONFIG'

    nombre_categoria = db.Column('NOMBRE_CATEGORIA', db.String(40), primary_key=True, comment="ID textual: 'Alimentación', 'Transporte'")
    icono_app = db.Column('ICONO_APP', db.String(50), comment='Nombre del asset local o URL')
    color_hex = db.Column('COLOR_HEX', db.String(7), comment='Para pintar el gráfico')
    mensaje_gasto_alto = db.Column('MENSAJE_GASTO_ALTO', db.String(150), comment="Ej: '¡Cuidado! Estás comiendo mucho fuera.'")
    mensaje_ahorro = db.Column('MENSAJE_AHORRO', db.String(150), comment="Ej: '¡Bien! Has reducido gastos aquí.'")

    # Relaciones
    gastos = db.relationship('GastoManual', backref='categoria_config', lazy=True)
    presupuestos = db.relationship('Presupuesto', backref='categoria_config', lazy=True)
    desgloses = db.relationship('DesgloseMovimiento', backref='categoria_config', lazy=True)

class Meta(db.Model):
    __tablename__ = 'METAS'

    meta_id = db.Column('META_ID', db.Integer, primary_key=True)
    user_uuid = db.Column('USER_UUID', db.String(50), db.ForeignKey('USUARIOS.USER_UUID'), nullable=False)
    titulo = db.Column('TITULO', db.String(100), nullable=False)
    monto_objetivo = db.Column('MONTO_OBJETIVO', db.Numeric(15, 2), nullable=False)
    monto_ahorrado = db.Column('MONTO_AHORRADO', db.Numeric(15, 2), default=0)
    fecha_limite = db.Column('FECHA_LIMITE', db.Date)
    icono_url = db.Column('ICONO_URL', db.String(255))
    estado = db.Column('ESTADO', db.String(20), default='EN_PROGRESO')

class GastoManual(db.Model):
    __tablename__ = 'GASTOS_MANUALES'

    id_gasto = db.Column('ID_GASTO', db.Integer, primary_key=True)
    user_uuid = db.Column('USER_UUID', db.String(50), db.ForeignKey('USUARIOS.USER_UUID'), nullable=False)
    monto = db.Column('MONTO', db.Numeric(15, 2), nullable=False)
    fecha_gasto = db.Column('FECHA_GASTO', db.DateTime, default=datetime.utcnow)
    categoria = db.Column('CATEGORIA', db.String(40), db.ForeignKey('CATEGORIAS_CONFIG.NOMBRE_CATEGORIA'), nullable=False)
    descripcion = db.Column('DESCRIPCION', db.String(100))
    es_gasto_hormiga = db.Column('ES_GASTO_HORMIGA', db.Boolean, default=False)

class Presupuesto(db.Model):
    __tablename__ = 'PRESUPUESTOS'

    presupuesto_id = db.Column('PRESUPUESTO_ID', db.Integer, primary_key=True)
    user_uuid = db.Column('USER_UUID', db.String(50), db.ForeignKey('USUARIOS.USER_UUID'), nullable=False)
    categoria = db.Column('CATEGORIA', db.String(40), db.ForeignKey('CATEGORIAS_CONFIG.NOMBRE_CATEGORIA'), nullable=False)
    limite_mensual = db.Column('LIMITE_MENSUAL', db.Numeric(15, 2), nullable=False)
    alerta_porcentaje = db.Column('ALERTA_PORCENTAJE', db.Integer, default=80, comment='Avisar al llegar al 80%')

class DesgloseMovimiento(db.Model):
    __tablename__ = 'DESGLOSE_MOVIMIENTOS'

    id_desglose = db.Column('ID_DESGLOSE', db.Integer, primary_key=True)
    user_uuid = db.Column('USER_UUID', db.String(50), db.ForeignKey('USUARIOS.USER_UUID'), nullable=False)
    id_trx_mainframe = db.Column('ID_TRX_MAINFRAME', db.String(26), nullable=False, comment='ID original del retiro en Mainframe')
    monto_parcial = db.Column('MONTO_PARCIAL', db.Numeric(15, 2), nullable=False)
    nueva_categoria = db.Column('NUEVA_CATEGORIA', db.String(40), db.ForeignKey('CATEGORIAS_CONFIG.NOMBRE_CATEGORIA'), nullable=False, comment='La categoría real del gasto efectivo')
    descripcion_nota = db.Column('DESCRIPCION_NOTA', db.String(100))
    fecha_registro = db.Column('FECHA_REGISTRO', db.DateTime, default=datetime.utcnow)
