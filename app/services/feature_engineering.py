from app.models.core_banking import Cliente, Cuenta, Tarjeta, Movimiento
from sqlalchemy import func
from datetime import datetime

class FeatureEngineeringService:
    """
    Servicio encargado de transformar los datos crudos transaccionales
    en un vector de características (features) para el modelo de ML.
    """

    @staticmethod
    def get_client_features(cod_cliente):
        """
        Obtiene y calcula las variables para un cliente específico.
        Retorna un diccionario con los datos agregados.
        """
        
        # 1. Obtener datos demográficos del cliente
        cliente = Cliente.query.filter_by(cod_cliente=cod_cliente).first()
        if not cliente:
            return None

        # Calcular edad
        edad = 0
        if cliente.fecha_nac:
            today = datetime.today()
            edad = today.year - cliente.fecha_nac.year - ((today.month, today.day) < (cliente.fecha_nac.month, cliente.fecha_nac.day))

        # 2. Obtener resumen de cuentas (Saldos)
        # Suma de saldo disponible de todas las cuentas activas
        total_saldo = db_sum_accounts(cod_cliente)
        num_cuentas = Cuenta.query.filter_by(cod_cliente=cod_cliente, estado='A').count()

        # 3. Obtener resumen de tarjetas
        num_tarjetas_credito = Tarjeta.query.filter_by(cod_cliente=cod_cliente, tipo_tarjeta='CREDITO', estado='A').count()

        # 4. Obtener métricas transaccionales (Movimientos)
        # Unimos Movimientos con Cuentas para filtrar por cliente
        stats_movimientos = db_transaction_stats(cod_cliente)

        # Construir el diccionario de features (Vector de entrada para el modelo)
        features = {
            "cod_cliente": cliente.cod_cliente,
            "edad": edad,
            "ingresos_mes": float(cliente.ingresos_mes or 0),
            "score_crediticio": cliente.score_crediticio,
            "total_saldo_cuentas": float(total_saldo or 0),
            "num_cuentas_activas": num_cuentas,
            "num_tarjetas_credito": num_tarjetas_credito,
            "total_monto_movimientos": float(stats_movimientos['total_monto'] or 0),
            "promedio_monto_movimientos": float(stats_movimientos['avg_monto'] or 0),
            "num_transacciones": stats_movimientos['count_trx']
        }

        return features

def db_sum_accounts(cod_cliente):
    """Helper para sumar saldos usando SQL directo vía SQLAlchemy"""
    from app.extensions import db
    result = db.session.query(func.sum(Cuenta.saldo_disponible))\
        .filter(Cuenta.cod_cliente == cod_cliente, Cuenta.estado == 'A')\
        .scalar()
    return result

def db_transaction_stats(cod_cliente):
    """Helper para calcular estadísticas de movimientos"""
    from app.extensions import db
    
    # Join Movimiento -> Cuenta -> Cliente
    # Queremos movimientos de las cuentas de ESTE cliente
    query = db.session.query(
        func.sum(Movimiento.monto).label('total_monto'),
        func.avg(Movimiento.monto).label('avg_monto'),
        func.count(Movimiento.id_trx).label('count_trx')
    ).join(Cuenta, Movimiento.num_cuenta == Cuenta.num_cuenta)\
     .filter(Cuenta.cod_cliente == cod_cliente)
    
    result = query.first()
    
    return {
        'total_monto': result.total_monto,
        'avg_monto': result.avg_monto,
        'count_trx': result.count_trx
    }
