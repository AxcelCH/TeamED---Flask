from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from app.services.core_banking_service import CoreBankingService
from app.services.watson_service import WatsonService
from app.models.mobile_app import Usuario, Meta, GamificacionAnimal
from app.models.core_banking import Cuenta
from app.extensions import db
from sqlalchemy import func
from datetime import datetime

coach_bp = Blueprint('coach', __name__, url_prefix='/api/v1/coach')

@coach_bp.route('/chat', methods=['POST'])
@jwt_required()
def chat_with_coach():
    """
    Endpoint para chatear con el Coach Financiero (Pulgarcito).
    Genera el contexto automáticamente y consulta a Watsonx.
    ---
    tags:
      - Coach Financiero
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: false
        schema:
          type: object
          properties:
            message:
              type: string
              description: Pregunta específica del usuario (Opcional). Si se omite, el coach da un consejo proactivo.
              example: "¿Cómo puedo ahorrar más para mi viaje?"
    responses:
      200:
        description: Respuesta del Coach generada por IA.
        schema:
          type: object
          properties:
            response:
              type: string
              description: El consejo o respuesta generada por Watsonx.
            context_used:
              type: object
              description: El contexto JSON que se envió al modelo (para depuración).
      400:
        description: Token inválido o error de solicitud.
      404:
        description: Datos no encontrados para generar contexto.
    """
    # 1. Reutilizar lógica de contexto (TRX005)
    # Llamamos internamente a la función que genera el contexto
    # Nota: Para hacerlo limpio, extraemos la lógica de get_coach_context a una función auxiliar o servicio
    # Pero por rapidez, invocamos la misma lógica aquí.
    
    claims = get_jwt()
    cod_cliente = claims.get("cod_cliente")
    user_uuid = claims.get("sub")
    
    if not cod_cliente:
        return jsonify({"msg": "Token inválido"}), 400

    # --- INICIO LÓGICA CONTEXTO (Copia simplificada de get_coach_context) ---
    mainframe_data = CoreBankingService.obtener_perfil_360(cod_cliente)
    if not mainframe_data:
        return jsonify({"msg": "Error obteniendo datos financieros"}), 404

    usuario = Usuario.query.filter_by(user_uuid=user_uuid).first()
    if not usuario:
        return jsonify({"msg": "Usuario no encontrado"}), 404
        
    top_cat_id = mainframe_data['spending_behavior'].get('top_categoria_id')
    animal_obj = None
    if top_cat_id:
        animal_obj = GamificacionAnimal.query.filter_by(id_categoria=top_cat_id).first()
    if not animal_obj:
        animal_obj = GamificacionAnimal.query.filter_by(nombre_animal='Perezoso').first()
    animal_nombre = animal_obj.nombre_animal if animal_obj else "Perezoso"
    
    # Metas
    metas_list = []
    metas_db = Meta.query.filter_by(user_uuid=user_uuid).order_by(Meta.fecha_limite.asc()).limit(3).all()
    for meta in metas_db:
        pct_real = (float(meta.monto_ahorrado) / float(meta.monto_objetivo)) * 100 if meta.monto_objetivo > 0 else 0
        metas_list.append({
            "titulo": meta.titulo,
            "monto_objetivo": float(meta.monto_objetivo),
            "progreso_actual": float(meta.monto_ahorrado),
            "porcentaje": round(pct_real, 1)
        })
        
    contexto_completo = {
        "mainframe_zos_connect": {
            "financial_health": mainframe_data['financial_health'],
            "spending_behavior": mainframe_data['spending_behavior']
        },
        "cloud_data": {
            "contexto_coach": {
                "perfil_usuario": {
                    "nickname": usuario.nickname,
                    "arquetipo_animal": animal_nombre
                },
                "seguimiento_metas": {
                    "metas_principales": metas_list
                }
            }
        }
    }
    # --- FIN LÓGICA CONTEXTO ---

    # 2. Obtener mensaje del usuario (si existe)
    data = request.get_json() or {}
    user_message = data.get('message')

    # 3. Llamar a Watsonx
    respuesta_coach = WatsonService.generar_consejo_coach(contexto_completo, user_message)
    
    return jsonify({
        "response": respuesta_coach,
        "context_used": contexto_completo # Opcional, para debug
    }), 200

@coach_bp.route('/context', methods=['GET'])
@jwt_required()
def get_coach_context():
    """
    TRX005: Contexto para el Agente Coach Financiero (Pulgarcito).
    Combina datos del Mainframe (Salud Financiera) con datos de la Nube (Metas, Perfil).
    ---
    tags:
      - Coach Financiero
    security:
      - Bearer: []
    responses:
      200:
        description: Contexto JSON consolidado para el prompt del LLM.
        schema:
          type: object
          properties:
            mainframe_zos_connect:
              type: object
              properties:
                financial_health:
                  type: object
                spending_behavior:
                  type: object
            cloud_data:
              type: object
              properties:
                contexto_coach:
                  type: object
                  properties:
                    perfil_usuario:
                      type: object
                    seguimiento_metas:
                      type: object
    """
    claims = get_jwt()
    cod_cliente = claims.get("cod_cliente")
    user_uuid = claims.get("sub") # O user_uuid si es diferente
    
    if not cod_cliente:
        return jsonify({"msg": "Token inválido"}), 400

    # 1. Obtener Datos Mainframe (TRX005 Core)
    mainframe_data = CoreBankingService.obtener_perfil_360(cod_cliente)
    if not mainframe_data:
        return jsonify({"msg": "Cliente no encontrado en Core Banking"}), 404

    # 2. Obtener Datos Cloud (Usuario y Metas)
    usuario = Usuario.query.filter_by(user_uuid=user_uuid).first()
    if not usuario:
        # Fallback si no existe en tabla USUARIOS (raro si tiene token)
        return jsonify({"msg": "Usuario no encontrado en App Data"}), 404

    # Obtener Animal y Nivel (Recalculado o almacenado)
    # Para consistencia, usamos la lógica de Products (TRX004) o lo que esté guardado.
    # El prompt pide "De CLOUD_USUARIOS", así que usamos lo guardado en DB si existe,
    # pero idealmente deberíamos refrescarlo.
    # Vamos a refrescarlo usando los datos de Mainframe recién traídos.
    
    top_cat_id = mainframe_data['spending_behavior'].get('top_categoria_id')
    
    # Buscar Animal
    animal_obj = None
    if top_cat_id:
        animal_obj = GamificacionAnimal.query.filter_by(id_categoria=top_cat_id).first()
    if not animal_obj:
        animal_obj = GamificacionAnimal.query.filter_by(nombre_animal='Perezoso').first()
        
    animal_nombre = animal_obj.nombre_animal if animal_obj else "Perezoso"
    
    # Calcular Nivel (Sufijo)
    patron = mainframe_data['spending_behavior']['patron_consumo']
    qty_peq = patron['transacciones_pequenas']
    qty_med = patron['transacciones_medianas']
    qty_gra = patron['transacciones_grandes']
    total_tx = qty_peq + qty_med + qty_gra
    
    nivel_animal = 1 # Default
    suffix = "Novato"
    if total_tx > 0:
        if qty_gra >= qty_med and qty_gra >= qty_peq:
            suffix = "Legendario"
            nivel_animal = 3
        elif qty_med >= qty_peq:
            suffix = "Master"
            nivel_animal = 2
        else:
            suffix = "Junior"
            nivel_animal = 1
            
    # 3. Procesar Metas
    metas_list = []
    # Traer 3 metas principales (por fecha límite más cercana o prioridad)
    metas_db = Meta.query.filter_by(user_uuid=user_uuid).order_by(Meta.fecha_limite.asc()).limit(3).all()
    
    for meta in metas_db:
        # Calcular Riesgo
        riesgo = "BAJO"
        if meta.monto_objetivo > 0:
            pct_real = (float(meta.monto_ahorrado) / float(meta.monto_objetivo)) * 100
            
            # Días totales vs Días pasados (Estimación simple)
            # Asumimos fecha inicio = created_at (si existiera) o simplemente fecha limite vs hoy
            # Heurística simple: Si falta poco tiempo y falta mucho dinero -> ALTO
            days_remaining = (meta.fecha_limite - datetime.now().date()).days
            
            if days_remaining < 0:
                riesgo = "VENCIDO"
            elif pct_real >= 100:
                riesgo = "COMPLETADO"
            elif days_remaining < 30 and pct_real < 80:
                riesgo = "ALTO"
            elif days_remaining < 90 and pct_real < 50:
                riesgo = "MEDIO"
        
        metas_list.append({
            "titulo": meta.titulo,
            "monto_objetivo": float(meta.monto_objetivo),
            "progreso_actual": float(meta.monto_ahorrado),
            "porcentaje": round(pct_real, 1) if meta.monto_objetivo > 0 else 0,
            "fecha_limite": meta.fecha_limite.isoformat(),
            "riesgo_cumplimiento": riesgo
        })

    # Construir Respuesta Final
    response = {
        "mainframe_zos_connect": {
            "source": "mainframe_zos_connect",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "financial_health": mainframe_data['financial_health'],
            "spending_behavior": mainframe_data['spending_behavior']
        },
        "cloud_data": {
            "contexto_coach": {
                "perfil_usuario": {
                    "nickname": usuario.nickname,
                    "arquetipo_animal": animal_nombre,
                    "nivel_animal": nivel_animal,
                    "nivel_descripcion": suffix
                },
                "seguimiento_metas": {
                    "metas_principales": metas_list
                }
            }
        }
    }
    
    return jsonify(response), 200

@coach_bp.route('/check-purchase', methods=['POST'])
@jwt_required()
def check_purchase():
    """
    Consulta de Compra (Simulación).
    Verifica si una compra es viable según saldo y presupuesto.
    ---
    tags:
      - Coach Financiero
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - amount
          properties:
            amount:
              type: number
              description: Monto de la compra a simular.
            category_id:
              type: integer
              description: ID de la categoría de la compra (opcional).
    responses:
      200:
        description: Resultado de la simulación.
        schema:
          type: object
          properties:
            purchase_check:
              type: object
              properties:
                amount:
                  type: number
                can_afford:
                  type: boolean
                current_balance:
                  type: number
                remaining_balance:
                  type: number
                advice:
                  type: string
    """
    claims = get_jwt()
    cod_cliente = claims.get("cod_cliente")
    
    data = request.get_json()
    amount = data.get('amount', 0)
    category_id = data.get('category_id')
    
    if amount <= 0:
        return jsonify({"msg": "Monto inválido"}), 400
        
    # 1. Verificar Saldo
    liquidez = db.session.query(func.sum(Cuenta.saldo_disponible)).filter_by(cod_cliente=cod_cliente, estado='A').scalar() or 0.0
    
    can_afford = float(liquidez) >= amount
    
    return jsonify({
        "purchase_check": {
            "amount": amount,
            "can_afford": can_afford,
            "current_balance": float(liquidez),
            "remaining_balance": float(liquidez) - amount if can_afford else float(liquidez),
            "advice": "Compra viable." if can_afford else "Saldo insuficiente."
        }
    }), 200
