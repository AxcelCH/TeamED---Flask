from app.extensions import db
from datetime import datetime

class Cliente(db.Model):
    """
    Tabla CORE_CLIENTES: Información principal del cliente.
    """
    __tablename__ = 'CORE_CLIENTES'

    cod_cliente = db.Column(db.String(10), primary_key=True, nullable=False, comment='ID único interno (CIF)')
    dni_ruc = db.Column(db.String(11), nullable=False)
    nombres = db.Column(db.String(50), nullable=False)
    apellidos = db.Column(db.String(50), nullable=False)
    fecha_nac = db.Column(db.Date, nullable=False, comment='Vital para perfilamiento por edad')
    email = db.Column(db.String(60))
    telefono = db.Column(db.String(15))
    ingresos_mes = db.Column(db.Numeric(15, 2), comment='Base para calcular capacidad de deuda')
    score_crediticio = db.Column(db.Integer, comment='Score Sentinel/Infocorp')
    fecha_alta = db.Column(db.Date, default=datetime.utcnow)

    # Relaciones (para facilitar consultas en el ORM)
    cuentas = db.relationship('Cuenta', backref='cliente', lazy=True)
    tarjetas = db.relationship('Tarjeta', backref='cliente', lazy=True)

class Cuenta(db.Model):
    """
    Tabla CORE_CUENTAS: Cuentas bancarias del cliente.
    """
    __tablename__ = 'CORE_CUENTAS'

    num_cuenta = db.Column(db.String(20), primary_key=True, nullable=False, comment='CCI o interna')
    cod_cliente = db.Column(db.String(10), db.ForeignKey('CORE_CLIENTES.cod_cliente'), nullable=False)
    tipo_cuenta = db.Column(db.String(3), nullable=False, comment='AHO=Ahorro, CTE=Corriente, CTS')
    moneda = db.Column(db.String(3), default='PEN')
    saldo_contable = db.Column(db.Numeric(15, 2), nullable=False)
    saldo_disponible = db.Column(db.Numeric(15, 2), nullable=False)
    estado = db.Column(db.String(1), default='A', comment='A=Activa, B=Bloqueada, C=Cancelada')

    # Relaciones
    tarjetas = db.relationship('Tarjeta', backref='cuenta', lazy=True)
    movimientos = db.relationship('Movimiento', backref='cuenta', lazy=True)

class Tarjeta(db.Model):
    """
    Tabla CORE_TARJETAS: Tarjetas de débito o crédito asociadas.
    """
    __tablename__ = 'CORE_TARJETAS'

    num_tarjeta = db.Column(db.String(16), primary_key=True, nullable=False, comment='PAN enmascarado o token')
    num_cuenta = db.Column(db.String(20), db.ForeignKey('CORE_CUENTAS.num_cuenta'), nullable=False)
    cod_cliente = db.Column(db.String(10), db.ForeignKey('CORE_CLIENTES.cod_cliente'), nullable=False)
    tipo_tarjeta = db.Column(db.String(10), nullable=False, comment='DEBITO, CREDITO')
    marca = db.Column(db.String(10), comment='VISA, MC, AMEX')
    fecha_venc = db.Column(db.Date, nullable=False)
    estado = db.Column(db.String(1), default='A')

    # Relaciones
    movimientos = db.relationship('Movimiento', backref='tarjeta', lazy=True)

class Movimiento(db.Model):
    """
    Tabla CORE_MOVIMIENTOS: Transacciones históricas.
    """
    __tablename__ = 'CORE_MOVIMIENTOS'

    id_trx = db.Column(db.String(26), primary_key=True, nullable=False, comment='Timestamp + Secuencia única')
    num_cuenta = db.Column(db.String(20), db.ForeignKey('CORE_CUENTAS.num_cuenta'), nullable=False)
    num_tarjeta = db.Column(db.String(16), db.ForeignKey('CORE_TARJETAS.num_tarjeta'), nullable=True, comment='Null si es transferencia web')
    cuenta_destino_origen = db.Column(db.String(20), comment='Si es Salida: A quién envío. Si es Entrada: Quién me envía.')
    fecha_proceso = db.Column(db.DateTime, nullable=False)
    tipo_mov = db.Column(db.String(1), nullable=False, comment='D=Debito, C=Credito')
    monto = db.Column(db.Numeric(15, 2), nullable=False)
    moneda = db.Column(db.String(3), default='PEN')
    glosa_trx = db.Column(db.String(100), nullable=False, comment='Texto crudo para NLP (ej: STARBUCKS)')
    cod_canal = db.Column(db.String(4), comment='ATM, POS, APP, WEB')
    cod_comercio = db.Column(db.String(15))
    ubicacion_trx = db.Column(db.String(50))
    saldo_post_trx = db.Column(db.Numeric(15, 2), comment='Saldo remanente tras la operación')
