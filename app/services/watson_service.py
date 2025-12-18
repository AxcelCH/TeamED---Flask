import requests
import os
from flask import current_app

class WatsonService:
    """
    Servicio para interactuar con IBM Watsonx AI.
    """
    
    @staticmethod
    def _obtener_token():
        api_key = os.environ.get('WATSONX_API_KEY')
        url = "https://iam.cloud.ibm.com/identity/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "urn:ibm:params:oauth:grant-type:apikey",
            "apikey": api_key
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()
            return response.json()["access_token"]
        except Exception as e:
            current_app.logger.error(f"Error obteniendo token Watson: {e}")
            return None

    @staticmethod
    def generar_consejo_coach(contexto_json, user_message=None):
        """
        Envía el contexto financiero a Watsonx para generar un consejo personalizado.
        Si user_message está presente, responde a esa pregunta específica.
        """
        token = WatsonService._obtener_token()
        if not token:
            return "Lo siento, no puedo conectar con mi cerebro financiero en este momento."

        project_id = os.environ.get('WATSONX_PROJECT_ID')
        url_watson = os.environ.get('WATSONX_URL')
        
        # Extraer datos clave para el prompt del sistema
        nickname = contexto_json['cloud_data']['contexto_coach']['perfil_usuario']['nickname']
        arquetipo = contexto_json['cloud_data']['contexto_coach']['perfil_usuario']['arquetipo_animal']
        
        # Prompt del Sistema (Adaptado del Notebook)
        system_prompt = f"""ROL: Eres "Pulgarcito", coach financiero de Intercounts360. Tu personalidad depende del arquetipo_animal recibido ({arquetipo}).

REGLAS DE ORO:
1. Brevedad: Máximo 2 parrafos cortos o 3 oraciones.
2. Datos Reales: Usa siempre el saldo_cuentas_ahorro (Mainframe) y el % de la meta (Nube).
3. Gamificación: Usa emojis según el arquetipo (🐻, 🦅, 🐜, etc).
4. Cero Invento: Si el dato no está en el JSON, no lo menciones.
5. Empatía: Saluda a {nickname} y sé motivador.

FORMATO DE SALIDA:
- Saludo con el nickname.
- Respuesta directa a la pregunta del usuario (si existe) o un consejo proactivo.
- Ánimo sobre su meta actual.
- Una pregunta final para interactuar."""

        # Construir el mensaje del usuario
        if user_message:
            content_user = f"Contexto Financiero:\n{contexto_json}\n\nPregunta del Usuario: {user_message}\n\nResponde a la pregunta usando el contexto."
        else:
            content_user = f"Analiza estos datos y dame un consejo proactivo:\n{contexto_json}"

        body = {
            "project_id": project_id,
            "model_id": "ibm/granite-3-3-8b-instruct",
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": content_user
                }
            ],
            "max_tokens": 500,
            "temperature": 0.7,
            "time_limit": 10000
        }
        
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }
        
        try:
            response = requests.post(url_watson, headers=headers, json=body)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            current_app.logger.error(f"Error llamando a Watsonx: {e}")
            if response:
                current_app.logger.error(f"Detalle Error: {response.text}")
            return "Tuve un problema analizando tus datos, pero recuerda: ¡El ahorro es la base de la fortuna!"
