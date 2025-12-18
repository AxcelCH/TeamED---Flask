from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from app.services.core_banking_service import CoreBankingService

products_bp = Blueprint('products', __name__, url_prefix='/api/v1')

@products_bp.route('/products', methods=['GET'])
@jwt_required()
def get_global_position():
    """
    Obtener Posición Global del Cliente (TRX001).
    
    Orquesta la transacción COBOL TRX001.
    El backend extrae el `cod_cliente` del Token JWT, consulta al Mainframe (o simulación)
    y cruza la información de Cuentas y Tarjetas para devolver una vista unificada.
    ---
    tags:
      - Productos Financieros
    security:
      - Bearer: []
    responses:
      200:
        description: Posición global obtenida exitosamente.
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                cuentas:
                  type: array
                  items:
                    type: object
                    properties:
                      nro_cuenta:
                        type: string
                        example: "191-1234567-0-99"
                        description: Número de cuenta formateado
                      moneda:
                        type: string
                        example: "PEN"
                        description: Moneda de la cuenta (PEN/USD)
                      saldo:
                        type: number
                        example: 1500.00
                        description: Saldo disponible
                      tarjeta_visual:
                        type: string
                        example: "4557 **** **** 1234"
                        description: Número de tarjeta enmascarado (o null si no tiene tarjeta asociada)
      400:
        description: Token inválido o sin cod_cliente.
      401:
        description: No autorizado (Token faltante o expirado).
    """
    # 1. Obtener claims del token (donde guardamos el cod_cliente en el login)
    claims = get_jwt()
    cod_cliente = claims.get("cod_cliente")
    
    if not cod_cliente:
        return jsonify({"msg": "Token inválido: No contiene cod_cliente"}), 400
    
    # 2. Invocar al Servicio del Core Banking (Simulación TRX001)
    # Ahora usamos directamente el Código de Cliente, mucho más eficiente.
    data_mainframe = CoreBankingService.obtener_posicion_global(cod_cliente)
    
    if not data_mainframe:
        # Caso: Cliente sin productos o error en Mainframe
        return jsonify({"data": {"cuentas": []}}), 200
        
    # 4. Lógica de Middleware: Cruce de Información (Match)
    # Recibimos listas planas del "Mainframe" y las cruzamos aquí.
    
    cuentas_raw = data_mainframe.get('TABLA-CUENTAS', [])
    tarjetas_raw = data_mainframe.get('TABLA-TARJETAS', [])
    
    lista_cuentas_final = []
    
    for cuenta in cuentas_raw:
        num_cuenta = cuenta['CTA-NUMERO']
        
        # Buscar si hay tarjeta asociada a esta cuenta en la lista de tarjetas
        # Usamos TRJ-CTA-LINK para hacer el match
        tarjeta_asociada = next((t for t in tarjetas_raw if t['TRJ-CTA-LINK'] == num_cuenta), None)
        
        tarjeta_visual = None
        if tarjeta_asociada:
            # Enmascarar tarjeta: 4557 **** **** 1234
            pan = tarjeta_asociada['TRJ-NUMERO']
            if len(pan) == 16:
                tarjeta_visual = f"{pan[:4]} **** **** {pan[-4:]}"
            else:
                tarjeta_visual = pan
        
        item_cuenta = {
            "nro_cuenta": num_cuenta,
            "moneda": cuenta['CTA-MONEDA'],
            "saldo": cuenta['CTA-SALDO'],
            "tarjeta_visual": tarjeta_visual
        }
        lista_cuentas_final.append(item_cuenta)
        
    return jsonify({
        "data": {
            "cuentas": lista_cuentas_final
        }
    }), 200

@products_bp.route('/accounts/<path:num_cuenta>/summary', methods=['GET'])
@jwt_required()
def get_account_summary(num_cuenta):
    """
    Obtener Detalle de Cuenta y Categorización (TRX002).
    
    Orquesta la transacción COBOL TRX002.
    El Mainframe calcula los totales por categoría y devuelve los últimos movimientos.
    ---
    tags:
      - Productos Financieros
    parameters:
      - name: num_cuenta
        in: path
        type: string
        required: true
        description: Número de cuenta (CCI o interno)
    responses:
      200:
        description: Resumen de cuenta obtenido exitosamente.
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                cabecera:
                  type: object
                  properties:
                    saldo:
                      type: number
                    moneda:
                      type: string
                resumen_categorias:
                  type: array
                  items:
                    type: object
                    properties:
                      categoria:
                        type: string
                      total:
                        type: number
                movimientos:
                  type: array
                  items:
                    type: object
                    properties:
                      fecha:
                        type: string
                      glosa:
                        type: string
                      monto:
                        type: number
                      categoria:
                        type: string
      404:
        description: Cuenta no encontrada.
    """
    # 1. Obtener claims del token (donde guardamos el cod_cliente en el login)
    claims = get_jwt()
    cod_cliente = claims.get("cod_cliente")
    
    if not cod_cliente:
        return jsonify({"msg": "Token inválido: No contiene cod_cliente"}), 400

    # 2. Invocar al Servicio del Core Banking (Simulación TRX002)
    # Pasamos cod_cliente para validar propiedad
    data_mainframe = CoreBankingService.obtener_detalle_cuenta(num_cuenta, cod_cliente)
    
    if not data_mainframe:
        return jsonify({"msg": "Cuenta no encontrada o error en Mainframe"}), 404
        
    # 2. Transformación de Middleware (Mapping COBOL -> JSON App)
    
    # Cabecera
    # Nota: Asumimos moneda PEN por defecto o la sacamos de otra consulta si fuera necesario.
    # En TRX002 simplificado solo viene saldo.
    cabecera = {
        "saldo": data_mainframe.get('SALDO-ACTUAL'),
        "moneda": "PEN" # Podría venir del COBOL si se agrega al copybook
    }
    
    # Resumen Categorías (Viene listo del COBOL)
    resumen_categorias = []
    for item in data_mainframe.get('TABLA-RESUMEN', []):
        resumen_categorias.append({
            "categoria": item['CAT-NOMBRE'],
            "total": item['CAT-TOTAL']
        })
        
    # Movimientos
    movimientos = []
    for mov in data_mainframe.get('TABLA-MOVS', []):
        movimientos.append({
            "fecha": mov['MOV-FECHA'],
            "glosa": mov['MOV-GLOSA'],
            "monto": mov['MOV-MONTO'],
            "categoria": mov['MOV-CAT-DESC']
        })
        
    return jsonify({
        "data": {
            "cabecera": cabecera,
            "resumen_categorias": resumen_categorias,
            "movimientos": movimientos
        }
    }), 200
        

