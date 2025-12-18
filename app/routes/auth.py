from flask import Blueprint, request, jsonify
from app.models.mobile_app import Usuario, TokenBlocklist
from app.services.core_banking_service import CoreBankingService
from app.extensions import db
from flask_jwt_extended import create_access_token, jwt_required, get_jwt
import uuid
import random

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Registrar un nuevo usuario en la App Móvil.
    ---
    tags:
      - Autenticación
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - dni
            - password
          properties:
            dni:
              type: string
              description: DNI del usuario (debe existir en Core Banking idealmente)
              example: "12345678"
            password:
              type: string
              description: Contraseña para la app
              example: "mi_password_seguro"
            nickname:
              type: string
              description: Nombre de usuario visible
              example: "Jeremi"
    responses:
      201:
        description: Usuario creado exitosamente
      400:
        description: Faltan datos o usuario ya existe
    """
    data = request.get_json()
    
    dni = data.get('dni')
    password = data.get('password')
    nickname = data.get('nickname')
    
    if not dni or not password:
        return jsonify({"msg": "Faltan datos (dni, password)"}), 400
        
    if Usuario.query.filter_by(dni_vinculado=dni).first():
        return jsonify({"msg": "El usuario ya existe"}), 400
        
    # Validar que el DNI exista en el Core Bancario (Mainframe)
    # Solo clientes del banco pueden registrarse en la App
    cliente_core = CoreBankingService.obtener_cliente(dni)
    if not cliente_core:
        return jsonify({"msg": "El DNI no corresponde a un cliente activo del banco"}), 400

    # Crear nuevo usuario
    # El user_uuid será el código de cliente del mainframe
    user_uuid = str(cliente_core['cod_cliente'])
    
    new_user = Usuario(
        user_uuid=user_uuid,
        dni_vinculado=dni,
        nickname=nickname
    )
    new_user.set_password(password)
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({"msg": "Usuario registrado exitosamente", "user_uuid": user_uuid}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Iniciar sesión y obtener Token JWT.
    ---
    tags:
      - Autenticación
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - dni
            - password
          properties:
            dni:
              type: string
              example: "12345678"
            password:
              type: string
              example: "mi_password_seguro"
    responses:
      200:
        description: Login exitoso. Retorna token y datos combinados del App y Mainframe.
        schema:
          type: object
          properties:
            msg:
              type: string
              example: "Login exitoso"
            access_token:
              type: string
              description: Token JWT para autenticar futuras peticiones
            user:
              type: object
              description: Datos del usuario (App + Core Bancario)
              properties:
                nickname:
                  type: string
                  example: "Jeremi"
                dni:
                  type: string
                  example: "12345678"
                cod_cliente:
                  type: string
                  description: Código único del cliente en el Mainframe (Core Bancario)
                  example: "CLI888888"
                nivel:
                  type: integer
                  description: Nivel de gamificación
                  example: 1
                animal:
                  type: string
                  description: Animal asociado al nivel
                  example: "Perezoso"
      401:
        description: Credenciales inválidas o Cliente no encontrado en Core Bancario
    """
    data = request.get_json()
    
    dni = data.get('dni')
    password = data.get('password')
    
    if not dni or not password:
        return jsonify({"msg": "Faltan datos"}), 400
        
    user = Usuario.query.filter_by(dni_vinculado=dni).first()
    
    if not user or not user.check_password(password):
        return jsonify({"msg": "Credenciales inválidas"}), 401
        
    # 2. Validar contra Mainframe y obtener Código de Cliente
    cliente_core = CoreBankingService.obtener_cliente(dni)
    if not cliente_core:
        return jsonify({"msg": "Cliente no encontrado en Core Bancario"}), 401
        
    cod_cliente = cliente_core.get('cod_cliente')

    # Crear token de acceso
    # Podemos incluir el cod_cliente en el token si es útil para futuras peticiones
    additional_claims = {"cod_cliente": cod_cliente}
    access_token = create_access_token(identity=user.user_uuid, additional_claims=additional_claims)
    
    return jsonify({
        "msg": "Login exitoso",
        "access_token": access_token,
        "user": {
            "nickname": user.nickname,
            "dni": user.dni_vinculado,
            "cod_cliente": cod_cliente,
            "nivel": user.nivel_financiero,
            "animal": user.animal_actual
        }
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Cerrar sesión (Revocar Token).
    Agrega el token actual a la lista negra para que no pueda ser usado nuevamente.
    ---
    tags:
      - Autenticación
    security:
      - Bearer: []
    responses:
      200:
        description: Logout exitoso
    """
    jti = get_jwt()["jti"]
    
    # Guardar JTI en la base de datos (Blocklist)
    db.session.add(TokenBlocklist(jti=jti))
    db.session.commit()
    
    return jsonify({"msg": "Logout exitoso. Token revocado."}), 200
