from flask import Flask
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "¡Hola! Mi API está viva en Render."

if __name__ == '__main__':
    # Esto es solo para probar en tu PC.
    # En producción, Gunicorn ignorará esto y usará sus propios comandos.
    app.run(debug=True)