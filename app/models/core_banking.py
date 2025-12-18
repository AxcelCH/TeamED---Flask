from app.extensions import db
from datetime import datetime

class Cliente(db.Model):
    """
    Tabla CORE_CLIENTES: Información principal del cliente.
    """
    __tablename__ = 'CORE_CLIENTES'

    cod_cliente = db.Column('COD_CLIENTE', db.String(10), primary_key=True, comment='ID único interno')
    dni_ruc = db.Column('DNI_RUC', db.String(11), nullable=False)
    nombres = db.Column('NOMBRES', db.String(50), nullable=False)
    apellidos = db.Column('APELLIDOS', db.String(50), nullable=False)
    fecha_nac = db.Column('FECHA_NAC', db.Date, nullable=False, comment='Vital para perfilamiento por edad')
    email = db.Column('EMAIL', db.String(60))
    telefono = db.Column('TELEFONO', db.String(15))
    ingresos_mes = db.Column('INGRESOS_MES', db.Numeric(15, 2), comment='Base para calcular capacidad de deuda')
    score_crediticio = db.Column('SCORE_CREDITICIO', db.Integer, comment='Score Sentinel/Infocorp')
    fecha_alta = db.Column('FECHA_ALTA', db.Date, default=datetime.utcnow)

    # Relaciones
    cuentas = db.relationship('Cuenta', backref='cliente', lazy=True)
    tarjetas = db.relationship('Tarjeta', backref='cliente', lazy=True)

class CategoriaCore(db.Model):
    """
    Tabla CORE_CATEGORIAS: Maestro de categorías del banco.
    """
    __tablename__ = 'CORE_CATEGORIAS'
    
    id_categoria = db.Column('ID_CATEGORIA', db.Integer, primary_key=True, autoincrement=True)
    nombre_categoria = db.Column('NOMBRE_CATEGORIA', db.String(50), nullable=False)
    
    # Relación con MCC
    mccs = db.relationship('MccCore', backref='categoria', lazy=True)

class Tarjeta(db.Model):
    """
    Tabla CORE_TARJETAS: Tarjetas de débito o crédito asociadas.
    """
    __tablename__ = 'CORE_TARJETAS'

    num_tarjeta = db.Column('NUM_TARJETA', db.String(16), primary_key=True, comment='PAN enmascarado o token')
    num_cuenta = db.Column('NUM_CUENTA', db.String(20), db.ForeignKey('CORE_CUENTAS.NUM_CUENTA'), nullable=True)
    cod_cliente = db.Column('COD_CLIENTE', db.String(10), db.ForeignKey('CORE_CLIENTES.COD_CLIENTE'), nullable=False)
    tipo_tarjeta = db.Column('TIPO_TARJETA', db.String(10), nullable=False, comment='DEBITO, CREDITO')
    marca = db.Column('MARCA', db.String(10), comment='VISA, MC, AMEX')
    fecha_venc = db.Column('FECHA_VENC', db.Date, nullable=False)
    estado = db.Column('ESTADO', db.String(1), default='A')

class MccCore(db.Model):
    """
    Tabla CORE_MCC: Merchant Category Codes.
    Relaciona códigos de comercio con categorías.
    """
    __tablename__ = 'CORE_MCC'
    
    cod_mcc = db.Column('MCC', db.String(4), primary_key=True, comment='Código estándar de comercio o rubro')
    descripcion = db.Column('DESCRIPCION', db.String(100))
    id_categoria = db.Column('ID_CATEGORIA', db.Integer, db.ForeignKey('CORE_CATEGORIAS.ID_CATEGORIA'), nullable=False)

class Cuenta(db.Model):
    """
    Tabla CORE_CUENTAS: Cuentas bancarias del cliente.
    """
    __tablename__ = 'CORE_CUENTAS'

    num_cuenta = db.Column('NUM_CUENTA', db.String(20), primary_key=True, comment='CCI o interna')
    cod_cliente = db.Column('COD_CLIENTE', db.String(10), db.ForeignKey('CORE_CLIENTES.COD_CLIENTE'), nullable=False)
    tipo_cuenta = db.Column('TIPO_CUENTA', db.String(3), nullable=False, comment='AHO=Ahorro, CTE=Corriente, CTS')
    moneda = db.Column('MONEDA', db.String(3), default='PEN')
    saldo_contable = db.Column('SALDO_CONTABLE', db.Numeric(15, 2), nullable=False)
    saldo_disponible = db.Column('SALDO_DISPONIBLE', db.Numeric(15, 2), nullable=False)
    estado = db.Column('ESTADO', db.String(1), default='A', comment='A=Activa, B=Bloqueada, C=Cancelada')

    # Relaciones
    tarjetas = db.relationship('Tarjeta', backref='cuenta', lazy=True)
    movimientos = db.relationship('Movimiento', backref='cuenta', lazy=True)

class Movimiento(db.Model):
    """
    Tabla CORE_MOVIMIENTOS: Transacciones históricas.
    """
    __tablename__ = 'CORE_MOVIMIENTOS'

    id_trx = db.Column('ID_TRX', db.String(26), primary_key=True, comment='Timestamp + Secuencia única')
    num_cuenta = db.Column('NUM_CUENTA', db.String(20), db.ForeignKey('CORE_CUENTAS.NUM_CUENTA'), nullable=False)
    num_tarjeta = db.Column('NUM_TARJETA', db.String(16), db.ForeignKey('CORE_TARJETAS.NUM_TARJETA'), nullable=True)
    cuenta_destino_origen = db.Column('CUENTA_DESTINO_ORIGEN', db.String(20), comment='Contraparte de la trx')
    fecha_proceso = db.Column('FECHA_PROCESO', db.DateTime, nullable=False)
    tipo_mov = db.Column('TIPO_MOV', db.String(1), nullable=False, comment='D=Debito, C=Credito')
    monto = db.Column('MONTO', db.Numeric(15, 2), nullable=False)
    moneda = db.Column('MONEDA', db.String(3), default='PEN')
    glosa_trx = db.Column('GLOSA_TRX', db.String(100), nullable=False, comment='Texto crudo para NLP')
    cod_canal = db.Column('COD_CANAL', db.String(4), comment='ATM, POS, APP, WEB')
    cod_comercio = db.Column('COD_COMERCIO', db.String(15), db.ForeignKey('CORE_MCC.MCC'), nullable=True)
    ubicacion_trx = db.Column('UBICACION_TRX', db.String(50))
    saldo_post_trx = db.Column('SALDO_POST_TRX', db.Numeric(15, 2), comment='Saldo remanente')

