import os
from flask import Flask, redirect # Importamos redirect aquí
from rifas import bp as rifas_bp, init_db, login_manager, UPLOAD_FOLDER
from pathlib import Path

def create_app():
    """Crea y configura la aplicación Flask."""
    app = Flask(__name__)
    
    # Genera una clave secreta fuerte para sesiones y mensajes flash
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'un-secreto-muy-seguro-CR129x7848n')
    
    # Configuración de la base de datos y uploads
    app.config['DATABASE'] = os.path.join(app.root_path, 'rifas.sqlite')
    app.config['UPLOAD_FOLDER'] = Path(app.root_path) / UPLOAD_FOLDER
    
    # Crear el directorio de subidas si no existe
    if not app.config['UPLOAD_FOLDER'].exists():
        app.config['UPLOAD_FOLDER'].mkdir(parents=True)

    # Inicializar la DB y crear el superusuario
    with app.app_context():
        init_db()

    # Inicializar Flask-Login
    login_manager.init_app(app)

    # Registrar el Blueprint
    app.register_blueprint(rifas_bp)

    # Redireccionar la raíz a la lista de rifas
    @app.route('/')
    def index():
        return redirect('/rifas')

    return app

if __name__ == '__main__':
    # Usar variables de entorno para puerto y modo, o valores por defecto
    port = int(os.environ.get('PORT', 8080))
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=port)
