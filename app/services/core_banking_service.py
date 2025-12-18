from app.models.core_banking import Cliente, Cuenta, Tarjeta, Movimiento, CategoriaCore, MccCore
from app.extensions import db
from flask import current_app
from sqlalchemy import func, case, extract
from datetime import datetime
import requests

class CoreBankingService:
    """
    Servicio que abstrae la comunicación con el Core Bancario.
    Actualmente simula la conexión consultando la BD local (PostgreSQL).
    En el futuro, aquí se implementarán las llamadas HTTP a z/OS Connect o CICS.
    """

    @staticmethod
    def obtener_detalle_cuenta(num_cuenta: str, cod_cliente: int):
        """
        Simula la transacción TRX002 (Detalle de Cuenta y Categorización).
        Retorna saldo, resumen por categorías y últimos movimientos.
        Valida que la cuenta pertenezca al cliente.
        """
        use_mock = current_app.config.get('USE_MOCK_MAINFRAME', True)
        cics_url = current_app.config.get('MAINFRAME_CICS_URL')

        # --- MODO REAL (HTTP a Mainframe) ---
        if not use_mock and cics_url:
            try:
                # Asumimos endpoint /accounts/{id}/summary o similar
                url_trx002 = cics_url.replace('trx001', 'trx002') 
                current_app.logger.info(f"Consultando TRX002 en Mainframe: {url_trx002}")
                
                response = requests.post(url_trx002, json={"num_cuenta": num_cuenta, "cod_cliente": cod_cliente}, timeout=5)
                
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception as e:
                current_app.logger.error(f"Error TRX002 Mainframe: {e}")
                return None

        # --- MODO SIMULACIÓN (Mock con BD Local) ---
        current_app.logger.info(f"Usando MOCK local para TRX002. Cuenta: {num_cuenta}")
        
        # 1. Obtener Saldo (Cabecera) y Validar Propiedad
        cuenta = Cuenta.query.filter_by(num_cuenta=num_cuenta, cod_cliente=cod_cliente).first()
        if not cuenta:
            current_app.logger.warning(f"Cuenta {num_cuenta} no encontrada o no pertenece al cliente {cod_cliente}")
            return None
            
        saldo_actual = float(cuenta.saldo_disponible)
        
        # 2. Obtener Movimientos + Categoría (JOIN)
        # SELECT M.*, C.NOMBRE_CATEGORIA 
        # FROM CORE_MOVIMIENTOS M
        # LEFT JOIN CORE_MCC MCC ON M.COD_COMERCIO = MCC.COD_MCC
        # LEFT JOIN CORE_CATEGORIA C ON MCC.ID_CATEGORIA = C.ID_CATEGORIA
        # WHERE M.NUM_CUENTA = ...
        
        movimientos_query = db.session.query(
            Movimiento,
            CategoriaCore.nombre_categoria
        ).outerjoin(
            MccCore, Movimiento.cod_comercio == MccCore.cod_mcc
        ).outerjoin(
            CategoriaCore, MccCore.id_categoria == CategoriaCore.id_categoria
        ).filter(
            Movimiento.num_cuenta == num_cuenta
        ).order_by(Movimiento.fecha_proceso.desc()).limit(20).all()
        
        # 3. Lógica de Acumulación (La "Magia" del COBOL)
        acumuladores = {}
        lista_movs = []
        
        for mov, cat_nombre in movimientos_query:
            nombre_cat = cat_nombre if cat_nombre else "Otros"
            monto = float(mov.monto)
            
            # Solo sumamos gastos (Débitos) para el gráfico
            if mov.tipo_mov == 'D':
                acumuladores[nombre_cat] = acumuladores.get(nombre_cat, 0.0) + monto
            
            # Llenar lista de movimientos
            lista_movs.append({
                "MOV-FECHA": mov.fecha_proceso.strftime('%Y-%m-%d'),
                "MOV-GLOSA": mov.glosa_trx,
                "MOV-MONTO": monto,
                "MOV-CAT-DESC": nombre_cat
            })
            
        # 4. Formatear Matriz Resumen (Top 10)
        lista_resumen = []
        for cat, total in acumuladores.items():
            lista_resumen.append({
                "CAT-NOMBRE": cat,
                "CAT-TOTAL": total
            })
            
        # Retorno estructura COBOL
        return {
            "COD-RETORNO": "00",
            "SALDO-ACTUAL": saldo_actual,
            "TABLA-RESUMEN": lista_resumen, # Matriz 1
            "TABLA-MOVS": lista_movs        # Matriz 2
        }

    @staticmethod
    def obtener_cliente(dni: str):
        """
        Consulta si el cliente existe en el Core Bancario y devuelve sus datos básicos.
        Retorna un diccionario con {cod_cliente, nombres, ...} o None.
        """
        use_mock = current_app.config.get('USE_MOCK_MAINFRAME', True)
        cics_url = current_app.config.get('MAINFRAME_CICS_URL')
        
        # --- MODO REAL ---
        if not use_mock and cics_url:
            try:
                # Asumimos que existe un endpoint /cliente o que el mismo endpoint
                # puede devolver info del cliente. Por ahora usaremos una URL base + /cliente
                # o asumiremos que la URL configurada es un gateway.
                # Para simplificar, usaremos la misma URL base pero cambiando el path si fuera necesario,
                # o simplemente enviando un flag.
                # Aquí simularemos que es otro endpoint o el mismo.
                url_cliente = cics_url.replace('trx001', 'cliente') # Ejemplo de convención
                
                current_app.logger.info(f"Consultando Cliente en Mainframe: {url_cliente}")
                response = requests.post(url_cliente, json={"dni": dni}, timeout=5)
                
                if response.status_code == 200:
                    return response.json()
                return None
            except Exception as e:
                current_app.logger.error(f"Error consultando cliente Mainframe: {e}")
                return None

        # --- MODO SIMULACIÓN ---
        cliente = Cliente.query.filter_by(dni_ruc=dni).first()
        if cliente:
            return {
                "cod_cliente": cliente.cod_cliente,
                "nombres": cliente.nombres,
                "apellidos": cliente.apellidos,
                "email": cliente.email
            }
        return None

    @staticmethod
    def obtener_posicion_global(cod_cliente: str):
        """
        Simula la transacción TRX001 (Posición Global).
        Recibe el COD_CLIENTE (obtenido en el login) para optimizar la consulta.
        """
        use_mock = current_app.config.get('USE_MOCK_MAINFRAME', True)
        cics_url = current_app.config.get('MAINFRAME_CICS_URL')

        # --- MODO REAL (HTTP a Mainframe) ---
        if not use_mock and cics_url:
            try:
                current_app.logger.info(f"Conectando a Mainframe en: {cics_url}")
                # Enviamos cod_cliente en lugar de DNI
                response = requests.post(cics_url, json={"cod_cliente": cod_cliente}, timeout=5)
                
                if response.status_code == 200:
                    return response.json()
                else:
                    current_app.logger.error(f"Error Mainframe: {response.status_code} - {response.text}")
                    return None 
            except Exception as e:
                current_app.logger.error(f"Excepción conectando al Mainframe: {e}")
                return None

        # --- MODO SIMULACIÓN (Mock con BD Local) ---
        current_app.logger.info(f"Usando MOCK local para Core Banking. Cliente: {cod_cliente}")
        
        # 1. Validar Cliente (Opcional, pero bueno para consistencia)
        # Ya no buscamos por DNI, vamos directo por PK
        cliente = Cliente.query.get(cod_cliente)
        if not cliente:
            return None

        # 2. Obtener Cuentas (CURSOR CUENTAS)
        cuentas_orm = Cuenta.query.filter_by(cod_cliente=cod_cliente).all()
        
        lista_cuentas = []
        lista_tarjetas = []
        
        for c in cuentas_orm:
            lista_cuentas.append({
                "CTA-NUMERO": c.num_cuenta,
                "CTA-MONEDA": c.moneda,
                "CTA-SALDO": float(c.saldo_disponible)
            })
            
            # 3. Obtener Tarjetas (Vinculadas a la Cuenta)
            # En este esquema estricto, solo vemos tarjetas asociadas a cuentas (Débito)
            if c.num_tarjeta:
                lista_tarjetas.append({
                    "TRJ-NUMERO": c.num_tarjeta,
                    "TRJ-CTA-LINK": c.num_cuenta
                })

        return {
            "COD-RETORNO": "00",
            "TABLA-CUENTAS": lista_cuentas,
            "TABLA-TARJETAS": lista_tarjetas
        }

    @staticmethod
    def obtener_movimientos_paginados(num_cuenta: str, categoria: str, last_id: str = None, limit: int = 15):
        """
        Simula la transacción TRX003 (Consulta Detallada Paginada).
        Retorna movimientos filtrados por categoría con paginación por cursor (last_id).
        """
        use_mock = current_app.config.get('USE_MOCK_MAINFRAME', True)
        
        # --- MODO SIMULACIÓN (Mock con BD Local) ---
        current_app.logger.info(f"TRX003: Cuenta={num_cuenta}, Cat={categoria}, LastID={last_id}")
        
        # Construir Query Base
        # JOIN Movimiento -> MccCore -> CategoriaCore
        query = db.session.query(Movimiento).join(
            MccCore, Movimiento.cod_comercio == MccCore.cod_mcc
        ).join(
            CategoriaCore, MccCore.id_categoria == CategoriaCore.id_categoria
        ).filter(
            Movimiento.num_cuenta == num_cuenta,
            CategoriaCore.nombre_categoria == categoria
        )
        
        # Aplicar Paginación (Cursor)
        # Asumimos orden descendente por ID_TRX (que incluye timestamp)
        if last_id:
            query = query.filter(Movimiento.id_trx < last_id)
            
        # Ordenar y Limitar
        # Pedimos limit + 1 para saber si hay más páginas
        movimientos = query.order_by(Movimiento.id_trx.desc()).limit(limit + 1).all()
        
        has_more = len(movimientos) > limit
        if has_more:
            movimientos = movimientos[:limit] # Recortar al límite solicitado
            
        # Formatear Salida (Simulando estructura COBOL/JSON final)
        lista_movs = []
        for mov in movimientos:
            lista_movs.append({
                "id_transaccion": mov.id_trx,
                "fecha": mov.fecha_proceso.isoformat(),
                "glosa": mov.glosa_trx,
                "monto": float(mov.monto) * (-1 if mov.tipo_mov == 'D' else 1), # Signo negativo para gastos
                "moneda": mov.moneda
            })
            
        return {
            "meta": {
                "count": len(lista_movs),
                "has_more": has_more
            },
            "data": lista_movs
        }

    @staticmethod
    def obtener_metricas_financieras(cod_cliente: int):
        """
        Simula la transacción TRX004 (Análisis de Comportamiento Financiero).
        Retorna la categoría TOP y la distribución de gastos por tamaño.
        """
        use_mock = current_app.config.get('USE_MOCK_MAINFRAME', True)
        current_app.logger.info(f"TRX004: Análisis Financiero para Cliente={cod_cliente}")

        # 1. Determinar el mes de análisis
        # Intentamos usar el mes actual. Si no hay datos, buscamos el último mes con actividad.
        now = datetime.now()
        target_month = now.month
        target_year = now.year

        # Verificar si hay movimientos en el mes actual
        has_data = db.session.query(Movimiento).join(
            Cuenta, Movimiento.num_cuenta == Cuenta.num_cuenta
        ).filter(
            Cuenta.cod_cliente == cod_cliente,
            extract('month', Movimiento.fecha_proceso) == target_month,
            extract('year', Movimiento.fecha_proceso) == target_year
        ).first()

        if not has_data:
            # Fallback: Buscar la fecha máxima de movimientos para este cliente
            last_mov_date = db.session.query(func.max(Movimiento.fecha_proceso)).join(
                Cuenta, Movimiento.num_cuenta == Cuenta.num_cuenta
            ).filter(
                Cuenta.cod_cliente == cod_cliente
            ).scalar()

            if last_mov_date:
                target_month = last_mov_date.month
                target_year = last_mov_date.year
                current_app.logger.info(f"TRX004: Sin datos en mes actual. Usando último mes disponible: {target_month}/{target_year}")
            else:
                current_app.logger.warning("TRX004: Cliente sin movimientos históricos.")
                return {
                    "COD-RETORNO": "00",
                    "METRICAS-GASTO": {
                        "TOP-CATEGORIA": "Ninguna",
                        "QTY-PEQUENO": 0,
                        "QTY-MEDIANO": 0,
                        "QTY-GRANDE": 0
                    }
                }

        # Base Query: Movimientos de Gasto (Debito) del Cliente en el mes OBJETIVO
        base_query = db.session.query(Movimiento).join(
            Cuenta, Movimiento.num_cuenta == Cuenta.num_cuenta
        ).filter(
            Cuenta.cod_cliente == cod_cliente,
            Movimiento.tipo_mov == 'D',
            extract('month', Movimiento.fecha_proceso) == target_month,
            extract('year', Movimiento.fecha_proceso) == target_year
        )

        # QUERY 1: Top Categoría
        top_cat_result = db.session.query(
            CategoriaCore.nombre_categoria,
            func.sum(Movimiento.monto).label('total_gasto')
        ).join(
            MccCore, Movimiento.cod_comercio == MccCore.cod_mcc
        ).join(
            CategoriaCore, MccCore.id_categoria == CategoriaCore.id_categoria
        ).join(
            Cuenta, Movimiento.num_cuenta == Cuenta.num_cuenta
        ).filter(
            Cuenta.cod_cliente == cod_cliente,
            Movimiento.tipo_mov == 'D',
            extract('month', Movimiento.fecha_proceso) == target_month,
            extract('year', Movimiento.fecha_proceso) == target_year
        ).group_by(
            CategoriaCore.nombre_categoria
        ).order_by(
            func.sum(Movimiento.monto).desc()
        ).first()

        top_categoria = top_cat_result[0] if top_cat_result else "Ninguna"

        # QUERY 2: Clasificación por Tamaño (Pivot con CASE)
        # Pequeño (< 50), Mediano (50-200), Grande (> 200)
        metrics_result = base_query.with_entities(
            func.sum(case((Movimiento.monto < 50, 1), else_=0)).label('qty_pequeno'),
            func.sum(case((Movimiento.monto.between(50, 200), 1), else_=0)).label('qty_mediano'),
            func.sum(case((Movimiento.monto > 200, 1), else_=0)).label('qty_grande')
        ).first()

        qty_pequeno = int(metrics_result.qty_pequeno or 0)
        qty_mediano = int(metrics_result.qty_mediano or 0)
        qty_grande = int(metrics_result.qty_grande or 0)

        return {
            "COD-RETORNO": "00",
            "METRICAS-GASTO": {
                "TOP-CATEGORIA": top_categoria,
                "QTY-PEQUENO": qty_pequeno,
                "QTY-MEDIANO": qty_mediano,
                "QTY-GRANDE": qty_grande
            }
        }
