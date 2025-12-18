from app.models.core_banking import Cliente, Cuenta, Tarjeta, Movimiento, CategoriaCore, MccCore
from app.extensions import db
from flask import current_app
from sqlalchemy import func
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
        # LEFT JOIN CORE_CATEGORIAS C ON MCC.ID_CATEGORIA = C.ID_CATEGORIA
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
        for c in cuentas_orm:
            lista_cuentas.append({
                "CTA-NUMERO": c.num_cuenta,
                "CTA-MONEDA": c.moneda,
                "CTA-SALDO": float(c.saldo_disponible)
            })

        # 3. Obtener Tarjetas (CURSOR TARJETAS)
        # En la nueva estructura, consultamos directamente CORE_TARJETAS por COD_CLIENTE
        tarjetas_orm = Tarjeta.query.filter_by(cod_cliente=cod_cliente).all()
        
        lista_tarjetas = []
        for t in tarjetas_orm:
            lista_tarjetas.append({
                "TRJ-NUMERO": t.num_tarjeta,
                "TRJ-CTA-LINK": t.num_cuenta if t.num_cuenta else ""
            })

        return {
            "COD-RETORNO": "00",
            "TABLA-CUENTAS": lista_cuentas,
            "TABLA-TARJETAS": lista_tarjetas
        }
