# app.py (Configuración Principal de Flask)
import os
from flask import Flask, redirect # Importamos redirect aquí
from rifas import bp as rifas_bp, init_db, login_manager, UPLOAD_FOLDER
from pathlib import Path

# CORRECCIÓN: Se eliminan las importaciones del módulo 'movies' que no existe.
# from movies import bp as movies_bp, init_movie_db 

def create_app():
    """Crea y configura la aplicación Flask."""
    app = Flask(__name__)
    
    # Genera una clave secreta fuerte para sesiones y mensajes flash
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'un-secreto-muy-seguro-CR129x7848n')
    
    # Configuración de la base de datos y uploads
    # NOTA: Para PythonAnywhere, asegúrate de que 'rifas.sqlite' se cree en el directorio raíz del proyecto (/home/kenth1977/rifas/)
    app.config['DATABASE'] = os.path.join(app.root_path, 'rifas.sqlite')
    app.config['UPLOAD_FOLDER'] = Path(app.root_path) / UPLOAD_FOLDER
    
    # Crear el directorio de subidas si no existe
    if not app.config['UPLOAD_FOLDER'].exists():
        app.config['UPLOAD_FOLDER'].mkdir(parents=True) 

    # Inicializar la DB y crear el superusuario
    with app.app_context():
        init_db()
        # CORRECCIÓN: Se elimina la llamada a la inicialización de la DB de 'movies'.
        # init_movie_db() 

    # Inicializar Flask-Login
    login_manager.init_app(app)

    # Registrar Blueprints
    app.register_blueprint(rifas_bp)
    # CORRECCIÓN: Se elimina el registro del blueprint de 'movies'.
    # app.register_blueprint(movies_bp)

    # Redireccionar la raíz a la lista de rifas
    @app.route('/')
    def index():
        return redirect('/rifas')

    return app

# CAMBIO CLAVE PARA PYTHONANYWHERE:
# Llamar a create_app() y asignar la instancia a 'app' para que el archivo WSGI
# pueda importarla con la línea: from app import app as application
app = create_app()

if __name__ == '__main__':
    # Usar la variable 'app' que ya creamos arriba
    port = int(os.environ.get('PORT', 8080))
    app.run(debug=True, host='0.0.0.0', port=port)
