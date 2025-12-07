from app.models.core_banking import Cliente, Cuenta, Tarjeta, Movimiento
from sqlalchemy import func
from datetime import datetime

class FeatureEngineeringService:
    """
    Servicio encargado de transformar los datos crudos transaccionales
    en un vector de características (features) para el modelo de ML.
    """

    @staticmethod
    def get_client_features(dni):
        """
        Obtiene y calcula las variables para un cliente específico buscando por DNI.
        Retorna un diccionario con los datos agregados.
        """
        
        # 1. Obtener datos demográficos del cliente usando DNI
        cliente = Cliente.query.filter_by(dni_ruc=dni).first()
        if not cliente:
            return None
        
        # Obtenemos el código interno para buscar en las otras tablas
        cod_cliente = cliente.cod_cliente

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

    @staticmethod
    def get_training_dataset(limit=1000):
        """
        Obtiene el dataset completo para entrenamiento usando una consulta SQL optimizada.
        Evita el problema N+1 y reduce la carga en memoria.
        """
        from app.extensions import db
        from sqlalchemy import text

        # Consulta SQL optimizada que hace todo el trabajo en la base de datos
        sql = text("""
            SELECT 
                c."COD_CLIENTE",
                c."FECHA_NAC",
                c."INGRESOS_MES",
                c."SCORE_CREDITICIO",
                -- Subquery para cuentas (Suma de saldos y conteo)
                (SELECT COALESCE(SUM("SALDO_DISPONIBLE"), 0) 
                 FROM "CORE_CUENTAS" cu 
                 WHERE cu."COD_CLIENTE" = c."COD_CLIENTE" AND cu."ESTADO" = 'A') as total_saldo_cuentas,
                (SELECT COUNT(*) 
                 FROM "CORE_CUENTAS" cu 
                 WHERE cu."COD_CLIENTE" = c."COD_CLIENTE" AND cu."ESTADO" = 'A') as num_cuentas_activas,
                -- Subquery para tarjetas de crédito
                (SELECT COUNT(*) 
                 FROM "CORE_TARJETAS" t 
                 WHERE t."COD_CLIENTE" = c."COD_CLIENTE" AND t."TIPO_TARJETA" = 'CREDITO' AND t."ESTADO" = 'A') as num_tarjetas_credito,
                -- Subquery para movimientos (Suma, Promedio, Conteo)
                (SELECT COALESCE(SUM(m."MONTO"), 0) 
                 FROM "CORE_MOVIMIENTOS" m 
                 JOIN "CORE_CUENTAS" cu ON m."NUM_CUENTA" = cu."NUM_CUENTA" 
                 WHERE cu."COD_CLIENTE" = c."COD_CLIENTE") as total_monto_movimientos,
                (SELECT COALESCE(AVG(m."MONTO"), 0) 
                 FROM "CORE_MOVIMIENTOS" m 
                 JOIN "CORE_CUENTAS" cu ON m."NUM_CUENTA" = cu."NUM_CUENTA" 
                 WHERE cu."COD_CLIENTE" = c."COD_CLIENTE") as promedio_monto_movimientos,
                (SELECT COUNT(*) 
                 FROM "CORE_MOVIMIENTOS" m 
                 JOIN "CORE_CUENTAS" cu ON m."NUM_CUENTA" = cu."NUM_CUENTA" 
                 WHERE cu."COD_CLIENTE" = c."COD_CLIENTE") as num_transacciones
            FROM "CORE_CLIENTES" c
            LIMIT :limit
        """)

        result = db.session.execute(sql, {'limit': limit})
        
        dataset = []
        today = datetime.today()

        for row in result:
            # Calcular edad en Python (es rápido y evita SQL complejo con fechas)
            edad = 0
            if row.FECHA_NAC:
                edad = today.year - row.FECHA_NAC.year - ((today.month, today.day) < (row.FECHA_NAC.month, row.FECHA_NAC.day))

            dataset.append({
                "cod_cliente": row.COD_CLIENTE,
                "edad": edad,
                "ingresos_mes": float(row.INGRESOS_MES or 0),
                "score_crediticio": row.SCORE_CREDITICIO,
                "total_saldo_cuentas": float(row.total_saldo_cuentas or 0),
                "num_cuentas_activas": row.num_cuentas_activas,
                "num_tarjetas_credito": row.num_tarjetas_credito,
                "total_monto_movimientos": float(row.total_monto_movimientos or 0),
                "promedio_monto_movimientos": float(row.promedio_monto_movimientos or 0),
                "num_transacciones": row.num_transacciones
            })
        
        return dataset

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
