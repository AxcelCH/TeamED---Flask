from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import datetime

app = Flask(__name__)
CORS(app)

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
ZOS_URL = "http://localhost:5000/api/clientes/demo/dashboard" # url de prueba en la pc local
ZOS_USER = "TU_USUARIO"
ZOS_PASS = "TU_PASSWORD"

# ==========================================
# 2. LÓGICA DE NEGOCIO (INTELIGENCIA FINANCIERA)
# ==========================================
def analizar_finanzas(movimientos):
    """
    Recibe la lista de movimientos, calcula el balance y define el perfil.
    """
    total_ingresos = 0.0
    total_gastos = 0.0

    # Calculamos sumas basándonos en TIPO_MOV ('C'redito / 'D'ebito) - C = ingreso, D = gasto
    for m in movimientos:
        monto = float(m['monto'])
        if m['tipo'] == 'C':
            total_ingresos += monto
        elif m['tipo'] == 'D':
            total_gastos += monto

    # Balance actual
    balance = total_ingresos - total_gastos

    # Algoritmo de Personalidad Financiera
    if total_ingresos == 0:
        perfil = "Cuenta Inactiva"
        desc = "No se detectaron ingresos recientes."
        nivel = 0
    elif total_gastos > total_ingresos:
        perfil = "Gastador Impulsivo"
        desc = "Tus gastos superan tus ingresos. ¡Alerta de sobreendeudamiento!"
        nivel = 1
    elif total_gastos < (total_ingresos * 0.3):
        perfil = "Ahorrador Estratégico"
        desc = "¡Excelente! Ahorras más del 70% de tus ingresos."
        nivel = 3
    else:
        perfil = "Inversor Equilibrado"
        desc = "Mantienes un buen balance, pero podrías optimizar gastos hormiga."
        nivel = 2

    return {
        "balance": round(balance, 2),
        "perfil_nombre": perfil,
        "perfil_desc": desc,
        "perfil_nivel": nivel
    }

# ==========================================
# 3. ENDPOINT PRINCIPAL
# ==========================================
@app.route('/api/clientes/<cod_cliente>/dashboard', methods=['GET'])
def dashboard_cliente(cod_cliente):
    
    lista_movimientos = []
    origen = ""

    # ---------------------------------------------------------
    # CASO A: SIMULACIÓN (Usar ID 'demo' o si falla el Mainframe)
    # ---------------------------------------------------------
    if cod_cliente == 'demo' or cod_cliente == '0000000001':
        origen = "SIMULACION_LOCAL"
        # Datos quemados simulando la estructura de tu DB2
        lista_movimientos = [
            {"fecha": "2023-12-06", "descripcion": "ABONO HABERES", "monto": 4500.00, "tipo": "C", "moneda": "PEN"},
            {"fecha": "2023-12-05", "descripcion": "PAGO ALQUILER", "monto": 1200.00, "tipo": "D", "moneda": "PEN"},
            {"fecha": "2023-12-04", "descripcion": "COMPRA PLAZA VEA", "monto": 350.50, "tipo": "D", "moneda": "PEN"},
            {"fecha": "2023-12-02", "descripcion": "NETFLIX SUBSCRIPCION", "monto": 45.90, "tipo": "D", "moneda": "PEN"},
        ]

    # ---------------------------------------------------------
    # CASO B: CONEXIÓN AL MAINFRAME (z/OS Connect)
    # ---------------------------------------------------------
    else:
        origen = "MAINFRAME_ZOS"
        payload = { "DFHCOMMAREA": { "cod_cliente_in": cod_cliente } }
        
        try:
            response = requests.post(ZOS_URL, json=payload, auth=(ZOS_USER, ZOS_PASS), verify=False, timeout=5)
            
            if response.status_code == 200:
                data_zos = response.json()
                # OJO: Ajustar "lista_out" al nombre real que devuelva z/OS Connect
                raw_list = data_zos.get('DFHCOMMAREA', {}).get('lista_out', [])
                
                # Normalizamos los datos que vienen del Mainframe
                for item in raw_list:
                    lista_movimientos.append({
                        "fecha": item.get('OUT_FECHA_PROCESO'),
                        "descripcion": item.get('OUT_GLOSA_TRX'),
                        "monto": item.get('OUT_MONTO'),
                        "tipo": item.get('OUT_TIPO_MOV'), # Esperamos 'C' o 'D'
                        "moneda": item.get('OUT_MONEDA')
                    })
            else:
                return jsonify({"error": "Error del Mainframe", "detalle": response.text}), 502
                
        except Exception as e:
            # Si falla la conexión real, devolvemos error (o podrías activar simulación de emergencia aquí)
            return jsonify({"error": "Error de conexión", "detalle": str(e)}), 500

    # ---------------------------------------------------------
    # PROCESAMIENTO FINAL
    # ---------------------------------------------------------
    # Aquí aplicamos la inteligencia financiera sobre los datos (sean reales o simulados)
    analisis = analizar_finanzas(lista_movimientos)

    # Respuesta Final JSON para la App
    return jsonify({
        "status": "success",
        "cliente_id": cod_cliente,
        "origen_datos": origen,
        "resumen_financiero": {
            "balance_total": analisis['balance'],
            "personalidad": analisis['perfil_nombre'],
            "consejo": analisis['perfil_desc'],
            "nivel_educacion": analisis['perfil_nivel'] # 1, 2 o 3 para mostrar estrellitas en la UI
        },
        "historial_transacciones": lista_movimientos
    }), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)