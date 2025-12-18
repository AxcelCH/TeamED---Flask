from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from app.services.core_banking_service import CoreBankingService
from app.models.mobile_app import GamificacionAnimal
from app.extensions import db

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

@products_bp.route('/accounts/<string:num_cuenta>/details', methods=['GET'])
@jwt_required()
def get_account_details_paginated(num_cuenta):
    """
    Obtener Historial Detallado por Categoría (TRX003).
    
    Permite "scroll infinito" filtrando por categoría.
    ---
    tags:
      - Productos Financieros
    parameters:
      - in: path
        name: num_cuenta
        required: true
        type: string
      - in: query
        name: category
        required: true
        type: string
        description: Nombre exacto de la categoría (Ej. Alimentación)
      - in: query
        name: last_id
        required: false
        type: string
        description: ID de la última transacción recibida (para paginación)
    responses:
      200:
        description: Lista de movimientos paginada.
    """
    # 1. Validar Token y Propiedad (Seguridad)
    claims = get_jwt()
    cod_cliente = claims.get("cod_cliente")
    
    if not cod_cliente:
        return jsonify({"msg": "Token inválido"}), 400
        
    # Validar que la cuenta pertenezca al cliente (Reutilizamos lógica o consultamos DB)
    # Por eficiencia, podríamos confiar en que si el servicio no encuentra nada devuelve vacío,
    # pero lo ideal es validar propiedad antes.
    # Aquí asumiremos que el servicio valida o filtra por cuenta, y si la cuenta no es del cliente
    # simplemente no retornará nada o el servicio debería validar.
    # Para ser estrictos como en TRX002:
    # (Podríamos agregar un método simple de validación en el servicio o hacerlo aquí)
    
    # 2. Obtener parámetros
    from flask import request
    category = request.args.get('category')
    last_id = request.args.get('last_id')
    
    if not category:
        return jsonify({"msg": "El parámetro 'category' es obligatorio"}), 400
        
    # 3. Invocar Servicio (TRX003)
    # Nota: El servicio debería validar internamente que la cuenta sea del cliente si queremos seguridad total,
    # o pasamos el cod_cliente para que filtre.
    # En este caso, pasaremos solo num_cuenta y confiamos en que el atacante no adivine cuentas ajenas
    # O MEJOR: Modificamos el servicio para aceptar cod_cliente y validar.
    # Vamos a asumir que el servicio hace el filtro base.
    
    # Corrección: El servicio TRX003 implementado arriba solo recibe num_cuenta.
    # Deberíamos validar propiedad aquí antes de llamar.
    from app.models.core_banking import Cuenta
    cuenta_propia = Cuenta.query.filter_by(num_cuenta=num_cuenta, cod_cliente=cod_cliente).first()
    if not cuenta_propia:
         return jsonify({"msg": "Cuenta no encontrada o no autorizada"}), 404

    resultado = CoreBankingService.obtener_movimientos_paginados(num_cuenta, category, last_id)
    
    return jsonify(resultado), 200

@products_bp.route('/financial-personality', methods=['GET'])
@jwt_required()
def get_financial_personality():
    """
    Obtener Balance y Personalidad Financiera (TRX004).
    
    Analiza el comportamiento de gasto del usuario en el mes actual.
    El análisis se realiza a nivel GLOBAL (Cliente), agregando todas las cuentas del usuario.
    ---
    tags:
      - Productos Financieros
    security:
      - Bearer: []
    responses:
      200:
        description: Métricas y arquetipo financiero.
        schema:
          type: object
          properties:
            data:
              type: object
              properties:
                top_categoria:
                  type: string
                  description: Nombre de la categoría con mayor gasto.
                animal_financiero:
                  type: string
                  description: Nombre completo del arquetipo (Animal + Nivel).
                animal_base:
                  type: string
                  description: Nombre del animal base.
                nivel_gasto:
                  type: string
                  description: Nivel basado en tamaño de transacciones (Novato, Junior, Master, Legendario).
                url_icono:
                  type: string
                  description: URL relativa del icono del animal.
                descripcion:
                  type: string
                  description: Descripción del perfil financiero.
                metricas:
                  type: object
                  properties:
                    total_gastado:
                      type: number
                    transacciones_totales:
                      type: integer
                    distribucion_porcentual:
                      type: object
                      properties:
                        pequeno:
                          type: number
                        mediano:
                          type: number
                        grande:
                          type: number
    """
    # 1. Obtener cod_cliente del token
    claims = get_jwt()
    cod_cliente = claims.get("cod_cliente")
    
    if not cod_cliente:
        return jsonify({"msg": "Token inválido"}), 400

    # 2. Invocar Servicio (TRX004)
    # Pasamos cod_cliente para análisis global
    data_mainframe = CoreBankingService.obtener_metricas_financieras(cod_cliente)
    
    metricas = data_mainframe.get('METRICAS-GASTO', {})
    top_categoria = metricas.get('TOP-CATEGORIA', 'Ninguna')
    qty_peq = metricas.get('QTY-PEQUENO', 0)
    qty_med = metricas.get('QTY-MEDIANO', 0)
    qty_gra = metricas.get('QTY-GRANDE', 0)
    
    # 3. Lógica Middleware: Cálculo de Porcentajes
    total_tx = qty_peq + qty_med + qty_gra
    
    if total_tx > 0:
        pct_pequeno = round((qty_peq / total_tx) * 100, 1)
        pct_mediano = round((qty_med / total_tx) * 100, 1)
        pct_grande = round((qty_gra / total_tx) * 100, 1)
    else:
        pct_pequeno = pct_mediano = pct_grande = 0

    # 4. Lógica Middleware: Asignación de Animal (Gamificación)
    # Ahora basada en la Categoría TOP (ID)
    top_categoria_id = metricas.get('TOP-CATEGORIA-ID')
    
    animal_obj = None
    if top_categoria_id:
        animal_obj = GamificacionAnimal.query.filter_by(id_categoria=top_categoria_id).first()
    
    if not animal_obj:
        # Fallback: Perezoso (ID Categoria 0 o por nombre)
        animal_obj = GamificacionAnimal.query.filter_by(nombre_animal='Perezoso').first()
    
    animal_nombre = animal_obj.nombre_animal if animal_obj else "Perezoso"
    animal_icono = animal_obj.url_icono if animal_obj else "assets/animals/sloth.png"
    animal_desc = animal_obj.descripcion_perfil if animal_obj else "Aún no tienes un perfil definido."
    
    # 5. Lógica Middleware: Clasificación por Tamaño de Gasto (Sufijo)
    # Determina el "Nivel" del animal basado en la mayoría de transacciones
    suffix = "Novato"
    if total_tx > 0:
        # Encontrar el tipo de gasto predominante
        if qty_gra >= qty_med and qty_gra >= qty_peq:
            suffix = "Legendario" # Mayoría Grandes (>200)
        elif qty_med >= qty_peq:
            suffix = "Master"     # Mayoría Medianos (50-200)
        else:
            suffix = "Junior"     # Mayoría Pequeños (<50)
            
    animal_completo = f"{animal_nombre} {suffix}"
    
    return jsonify({
        "data": {
            "top_categoria": top_categoria,
            "animal_financiero": animal_completo,
            "animal_base": animal_nombre,
            "nivel_gasto": suffix,
            "animal_icono": animal_icono,
            "animal_descripcion": animal_desc,
            "distribucion_gastos": {
                "pequeno": {"qty": qty_peq, "percentage": pct_pequeno},
                "mediano": {"qty": qty_med, "percentage": pct_mediano},
                "grande": {"qty": qty_gra, "percentage": pct_grande}
            },
            "total_transacciones_mes": total_tx
        }
    }), 200

