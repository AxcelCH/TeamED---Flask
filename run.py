from app import create_app

app = create_app()

if __name__ == '__main__':
    # Ejecutar la aplicación en modo debug
    app.run(debug=True, port=5000)
