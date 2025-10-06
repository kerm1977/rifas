import sqlite3
import os
import secrets
import json # Necesario para manejar la lista de ganadores en JSON
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image

# Eliminamos la importación y simulación de FPDF para evitar errores.
# La generación de archivos es ahora en texto plano (.txt).

# --- Configuración y Blueprint ---

# Directorio para las imágenes subidas
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Definición del Blueprint
bp = Blueprint('rifas', __name__, template_folder='templates', url_prefix='/')

# Configuración de Flask-Login (se inicializará en app.py)
login_manager = LoginManager()
login_manager.login_view = 'rifas.login'

def get_db():
    """Establece la conexión a la base de datos."""
    db = sqlite3.connect(current_app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db

def allowed_file(filename):
    """Verifica si la extensión del archivo es permitida."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Modelos de Datos (Simulación de ORM con SQLite) ---

class User(UserMixin):
    """Clase de usuario para Flask-Login."""
    def __init__(self, id, email, password_hash, first_name, last_name_1, last_name_2, phone, sinpe_name, game_type, game_description, role='user'):
        self.id = id
        self.email = email
        self.password_hash = password_hash
        self.first_name = first_name
        self.last_name_1 = last_name_1
        self.last_name_2 = last_name_2
        self.phone = phone
        self.sinpe_name = sinpe_name
        self.game_type = game_type
        self.game_description = game_description
        self.role = role

    def is_superuser(self):
        return self.role == 'superuser'
    
    @staticmethod
    def get(user_id):
        db = get_db()
        user_data = db.execute('SELECT * FROM user WHERE id = ?', (user_id,)).fetchone()
        db.close()
        if user_data:
            return User(**user_data)
        return None

# Función de carga de usuario para Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)

# --- Funciones de Inicialización ---

def init_db():
    """Crea las tablas de la base de datos y el superusuario inicial."""
    db = get_db()
    
    # 1. Crear tabla de Usuario
    db.execute("""
        CREATE TABLE IF NOT EXISTS user (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            first_name TEXT NOT NULL,
            last_name_1 TEXT NOT NULL,
            last_name_2 TEXT,
            phone TEXT NOT NULL,
            sinpe_name TEXT,
            game_type TEXT,
            game_description TEXT,
            role TEXT NOT NULL
        );
    """)

    # 2. Crear tabla de Rifa
    # MODIFICACIÓN: Agregamos winning_numbers Y CAMPOS DE PAGO POR DEFECTO PARA LA RIFA
    db.execute("""
        CREATE TABLE IF NOT EXISTS raffle (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raffle_number TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            prize TEXT NOT NULL,
            detail TEXT NOT NULL,
            raffle_date DATE NOT NULL,
            raffle_time TEXT,
            image_filename TEXT NOT NULL,
            winning_numbers TEXT DEFAULT '[]', -- Almacenará un JSON string de números ganadores
            sinpe_name_default TEXT, -- NUEVO: Nombre del Sinpe de la RIFA
            sinpe_phone_default TEXT -- NUEVO: Teléfono del Sinpe de la RIFA
        );
    """)

    # 3. Crear tabla de Selecciones (Números vendidos)
    # MODIFICACIÓN: Agregamos la columna is_canceled y las de PAGO DEL CLIENTE
    db.execute("""
        CREATE TABLE IF NOT EXISTS selection (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            raffle_id INTEGER NOT NULL,
            number TEXT NOT NULL, -- Número de 00 a 99
            customer_name TEXT NOT NULL,
            customer_phone TEXT NOT NULL,
            selection_password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_canceled BOOLEAN DEFAULT 0, -- NUEVO: 0 = No cancelado, 1 = Cancelado
            payment_method TEXT DEFAULT 'No especificado', -- NUEVO: Forma de pago del cliente
            sinpe_name TEXT, -- NUEVO: Nombre del Sinpe del cliente (si eligió Sinpe)
            sinpe_phone TEXT, -- NUEVO: Teléfono del Sinpe del cliente (si eligió Sinpe)
            FOREIGN KEY (raffle_id) REFERENCES raffle(id),
            UNIQUE (raffle_id, number)
        );
    """)
    db.commit()

    # MIGRACIÓN: Asegurar que las nuevas columnas existan
    try:
        db.execute("ALTER TABLE selection ADD COLUMN is_canceled BOOLEAN DEFAULT 0")
        db.commit()
    except sqlite3.OperationalError:
        pass # Columna ya existe o error no relacionado
        
    try:
        db.execute("ALTER TABLE raffle ADD COLUMN winning_numbers TEXT DEFAULT '[]'")
        db.commit()
    except sqlite3.OperationalError:
        pass # Columna ya existe o error no relacionado
        
    try:
        # MIGRACIÓN: Nuevos campos de pago para la tabla raffle
        db.execute("ALTER TABLE raffle ADD COLUMN sinpe_name_default TEXT")
        db.execute("ALTER TABLE raffle ADD COLUMN sinpe_phone_default TEXT")
        db.commit()
    except sqlite3.OperationalError:
        pass # Columna ya existe
        
    try:
        # MIGRACIÓN: Nuevos campos de pago para la tabla selection
        db.execute("ALTER TABLE selection ADD COLUMN payment_method TEXT DEFAULT 'No especificado'")
        db.execute("ALTER TABLE selection ADD COLUMN sinpe_name TEXT")
        db.execute("ALTER TABLE selection ADD COLUMN sinpe_phone TEXT")
        db.commit()
    except sqlite3.OperationalError:
        pass # Columna ya existe

    # 4. Crear Superusuario permanente
    superuser_email = 'kenth1977@gmail.com'
    # Contraseña: CR129x7848n
    superuser_pass_hash = generate_password_hash('CR129x7848n')

    # Verificar si el superusuario ya existe
    existing_user = db.execute('SELECT id FROM user WHERE email = ?', (superuser_email,)).fetchone()
    
    if not existing_user:
        try:
            db.execute("""
                INSERT INTO user (email, password_hash, first_name, last_name_1, last_name_2, phone, sinpe_name, game_type, game_description, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                superuser_email,
                superuser_pass_hash,
                'Super',
                'Usuario',
                'Admin',
                '88888888',
                'Super Sinpe',
                'Otro',
                'Usuario Admin Permanente',
                'superuser'
            ))
            db.commit()
            print(f"Superusuario '{superuser_email}' creado exitosamente.")
        except sqlite3.IntegrityError:
            # En caso de que se haya insertado en otro hilo o proceso
            print("El superusuario ya existía.")
        except Exception as e:
            print(f"Error al crear el superusuario: {e}")

    db.close()

# --- Rutas de Autenticación (Mantenidas) ---

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('rifas.ver_rifas'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        db = get_db()
        user_data = db.execute('SELECT * FROM user WHERE email = ?', (email,)).fetchone()
        db.close()
        
        if user_data:
            user = User(**user_data)
            if check_password_hash(user.password_hash, password):
                login_user(user)
                flash('Inicio de sesión exitoso.', 'success')
                return redirect(url_for('rifas.ver_rifas'))
        
        flash('Email o contraseña incorrectos.', 'danger')

    return render_template('login.html', title='Iniciar Sesión')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('rifas.ver_rifas'))

    if request.method == 'POST':
        data = request.form
        email = data.form.get('email')
        password = data.form.get('password')
        confirm_password = data.form.get('confirm_password')

        # 1. Autogenerar contraseña si falta (Min 8 chars)
        if not password or len(password) < 8:
            password = secrets.token_urlsafe(8)
            flash(f"Contraseña autogenerada: {password}. Por favor, anótela.", 'info')
        
        # Usar la misma contraseña autogenerada para confirmar si también falta
        if not confirm_password or len(confirm_password) < 8:
            confirm_password = password

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('rifas.register'))

        # 2. Encriptar contraseña
        password_hash = generate_password_hash(password)

        db = get_db()
        
        # 3. Verificar email existente
        existing_user = db.execute('SELECT id FROM user WHERE email = ?', (email,)).fetchone()
        if existing_user:
            db.close()
            flash('Este email ya está registrado.', 'danger')
            return redirect(url_for('rifas.register'))

        try:
            db.execute("""
                INSERT INTO user (email, password_hash, first_name, last_name_1, last_name_2, phone, sinpe_name, game_type, game_description, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email,
                password_hash,
                data.get('first_name'),
                data.get('last_name_1'),
                data.get('last_name_2'),
                data.get('phone'),
                data.get('sinpe_name'),
                data.get('game_type'),
                data.get('game_description') if data.get('game_type') == 'Otro' else None,
                'user'
            ))
            db.commit()
            db.close()
            flash('Registro exitoso. ¡Ahora puedes iniciar sesión!', 'success')
            return redirect(url_for('rifas.login'))
        except Exception as e:
            db.close()
            flash(f'Ocurrió un error en el registro: {e}', 'danger')

    return render_template('register.html', title='Registro de Usuario')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión exitosamente.', 'success')
    return redirect(url_for('rifas.ver_rifas'))

# --- Rutas CRUD de Rifas (Superusuario) ---

@bp.route('/rifas')
def ver_rifas():
    """Vista pública para ver las rifas disponibles."""
    db = get_db()
    # MODIFICACIÓN: Traemos las nuevas columnas de Sinpe por defecto
    rifas_data = db.execute('SELECT *, sinpe_name_default, sinpe_phone_default FROM raffle ORDER BY raffle_date DESC').fetchall()
    db.close()
    
    # Procesar los números ganadores (JSON string a lista de Python)
    rifas = []
    for rifa in rifas_data:
        rifa_dict = dict(rifa)
        try:
            rifa_dict['winning_numbers'] = json.loads(rifa_dict['winning_numbers'])
        except (json.JSONDecodeError, TypeError):
            rifa_dict['winning_numbers'] = []
            
        rifas.append(rifa_dict)
        
    return render_template('ver_rifas.html', title='Rifas Disponibles', rifas=rifas)

@bp.route('/rifas/crear', methods=['GET', 'POST'])
@login_required
def crear_rifa():
    """Superuser: Formulario para crear una nueva rifa."""
    if not current_user.is_superuser():
        flash('Acceso denegado. Solo superusuarios pueden crear rifas.', 'danger')
        return redirect(url_for('rifas.ver_rifas'))

    if request.method == 'POST':
        data = request.form
        image_file = request.files.get('image')
        
        # Recolección de nuevos campos
        payment_method = data.get('payment_method')
        sinpe_name_default = data.get('sinpe_name_default') if payment_method == 'Sinpe' else None
        sinpe_phone_default = data.get('sinpe_phone_default') if payment_method == 'Sinpe' else None

        # 1. Validación de imagen
        if not image_file or image_file.filename == '' or not allowed_file(image_file.filename):
            flash('Debe subir una imagen válida (PNG, JPG, JPEG).', 'danger')
            return redirect(request.url)

        # 2. Guardar imagen y redimensionar/optimizar (opcional, pero buena práctica)
        filename = secure_filename(image_file.filename)
        filepath = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)
        
        try:
            img = Image.open(image_file)
            # Redimensionar para optimización web (ej. a un máximo de 800px de ancho)
            if img.width > 800:
                img = img.resize((800, int(img.height * 800 / img.width)), Image.LANCZOS)
            img.save(filepath)
        except Exception as e:
            flash(f'Error al procesar la imagen: {e}', 'danger')
            return redirect(request.url)

        # 3. Guardar en la DB
        try:
            db = get_db()
            db.execute("""
                INSERT INTO raffle (raffle_number, name, price, prize, detail, raffle_date, raffle_time, image_filename, winning_numbers, sinpe_name_default, sinpe_phone_default)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('raffle_number'),
                data.get('name'),
                float(data.get('price')),
                data.get('prize'),
                data.get('detail'),
                data.get('raffle_date'),
                data.get('raffle_time') or None, # Hora opcional
                filename,
                '[]', # Inicializar sin ganadores
                sinpe_name_default,
                sinpe_phone_default
            ))
            db.commit()
            db.close()
            flash('Rifa creada exitosamente.', 'success')
            return redirect(url_for('rifas.ver_rifas'))
        except sqlite3.IntegrityError:
            flash('Error: El número de rifa ya existe.', 'danger')
            # Intentar eliminar la imagen si la inserción falla
            if os.path.exists(filepath):
                os.remove(filepath)
            return redirect(request.url)
        except Exception as e:
            flash(f'Error al guardar la rifa: {e}', 'danger')
            if os.path.exists(filepath):
                os.remove(filepath)
            return redirect(request.url)

    return render_template('crear_rifa.html', title='Crear Nueva Rifa')


@bp.route('/rifas/editar/<int:raffle_id>', methods=['GET', 'POST'])
@login_required
def editar_rifa(raffle_id):
    """Superuser: Formulario para editar una rifa existente."""
    if not current_user.is_superuser():
        flash('Acceso denegado. Solo superusuarios pueden editar rifas.', 'danger')
        return redirect(url_for('rifas.ver_rifas'))

    db = get_db()
    # MODIFICACIÓN: Traemos las nuevas columnas de Sinpe por defecto
    rifa = db.execute('SELECT *, sinpe_name_default, sinpe_phone_default FROM raffle WHERE id = ?', (raffle_id,)).fetchone()

    if rifa is None:
        db.close()
        flash('Rifa no encontrada.', 'danger')
        return redirect(url_for('rifas.ver_rifas'))
    
    rifa_dict = dict(rifa) # Convertir a dict para fácil acceso

    if request.method == 'POST':
        data = request.form
        image_file = request.files.get('image')
        new_filename = rifa_dict['image_filename']
        filepath = None
        
        # Recolección de nuevos campos
        payment_method = data.get('payment_method')
        sinpe_name_default = data.get('sinpe_name_default') if payment_method == 'Sinpe' else None
        sinpe_phone_default = data.get('sinpe_phone_default') if payment_method == 'Sinpe' else None

        try:
            # 1. Manejo de la nueva imagen
            if image_file and image_file.filename != '' and allowed_file(image_file.filename):
                # Eliminar imagen anterior
                old_filepath = os.path.join(current_app.root_path, UPLOAD_FOLDER, rifa_dict['image_filename'])
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)

                # Guardar nueva imagen
                new_filename = secure_filename(image_file.filename)
                filepath = os.path.join(current_app.root_path, UPLOAD_FOLDER, new_filename)
                
                img = Image.open(image_file)
                if img.width > 800:
                    img = img.resize((800, int(img.height * 800 / img.width)), Image.LANCZOS)
                img.save(filepath)

            # 2. Actualizar en la DB
            db.execute("""
                UPDATE raffle SET
                    raffle_number = ?, name = ?, price = ?, prize = ?, detail = ?, 
                    raffle_date = ?, raffle_time = ?, image_filename = ?,
                    sinpe_name_default = ?, sinpe_phone_default = ?
                WHERE id = ?
            """, (
                data.get('raffle_number'),
                data.get('name'), # Nombre de la rifa faltaba aquí
                float(data.get('price')),
                data.get('prize'),
                data.get('detail'),
                data.get('raffle_date'),
                data.get('raffle_time') or None,
                new_filename,
                sinpe_name_default,
                sinpe_phone_default,
                raffle_id
            ))
            db.commit()
            flash('Rifa actualizada exitosamente.', 'success')
            return redirect(url_for('rifas.ver_rifas'))

        except sqlite3.IntegrityError:
            flash('Error: El número de rifa ya existe.', 'danger')
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
        except Exception as e:
            flash(f'Error al actualizar la rifa: {e}', 'danger')
            if os.path.exists(filepath):
                os.remove(filepath)
        finally:
            db.close()
    
    db.close()
    return render_template('editar_rifa.html', title=f'Editar Rifa: {rifa_dict["name"]}', rifa=rifa_dict)

# --- RUTA NUEVA: ELIMINAR RIFA ---
@bp.route('/rifas/eliminar/<int:raffle_id>', methods=['POST'])
@login_required
def eliminar_rifa(raffle_id):
    """Superuser: Elimina una rifa y sus datos asociados."""
    if not current_user.is_superuser():
        flash('Acceso denegado. Solo superusuarios pueden eliminar rifas.', 'danger')
        return redirect(url_for('rifas.ver_rifas'))

    db = get_db()
    rifa = db.execute('SELECT id, image_filename FROM raffle WHERE id = ?', (raffle_id,)).fetchone()
    
    if not rifa:
        db.close()
        flash('Error: Rifa no encontrada.', 'danger')
        return redirect(url_for('rifas.ver_rifas'))

    try:
        # 1. Eliminar todas las selecciones asociadas (en cascada)
        db.execute('DELETE FROM selection WHERE raffle_id = ?', (raffle_id,))
        
        # 2. Eliminar la rifa
        db.execute('DELETE FROM raffle WHERE id = ?', (raffle_id,))
        
        # 3. Eliminar la imagen del disco
        image_filepath = os.path.join(current_app.root_path, UPLOAD_FOLDER, rifa['image_filename'])
        if os.path.exists(image_filepath):
            os.remove(image_filepath)
        
        db.commit()
        flash('Rifa eliminada permanentemente, incluyendo todos sus números vendidos.', 'success')
        
    except Exception as e:
        # Hacemos rollback si algo falla
        db.rollback() 
        flash(f'Error al eliminar la rifa: {e}', 'danger')
        
    finally: # Aseguramos que la conexión se cierre
        db.close()
        
    return redirect(url_for('rifas.ver_rifas'))


# --- RUTA PARA ANUNCIAR GANADOR ---
@bp.route('/rifas/anunciar_ganador/<int:raffle_id>', methods=['POST'])
@login_required
def anunciar_ganador(raffle_id):
    """Superuser: Recibe los números ganadores y los guarda/elimina en la rifa."""
    if not current_user.is_superuser():
        flash('Acceso denegado. Solo superusuarios pueden anunciar ganadores.', 'danger')
        return redirect(url_for('rifas.ver_rifas'))

    action = request.form.get('winner_action', 'announce')
        
    try:
        db = get_db()
        
        if action == 'remove_winners':
            # Acción para ELIMINAR GANADORES
            db.execute("""
                UPDATE raffle SET winning_numbers = '[]' WHERE id = ?
            """, (raffle_id,))
            db.commit()
            flash('¡Ganadores eliminados! La rifa ha sido reseteada.', 'success')
            
            # Redirigir a la lista de rifas o al detalle (lista es más lógico después de un reset)
            return redirect(url_for('rifas.ver_rifas')) 
            
        else: # action == 'announce'
            # Acción para ANUNCIAR GANADORES (Lógica existente)
            numbers_str = request.form.get('winning_numbers') # "05, 12, 45"
            
            if not numbers_str:
                flash('Debe seleccionar al menos un número ganador.', 'danger')
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

            # Limpiar y validar los números (deben ser de 2 dígitos)
            raw_numbers = [n.strip() for n in numbers_str.split(',') if n.strip()]
            winning_numbers = []
            
            for num in raw_numbers:
                # Formatear a 2 dígitos si es un número válido
                try:
                    # Aseguramos que el número tenga exactamente 2 dígitos, ej: 5 -> "05"
                    formatted_num = f"{int(num):02d}" 
                    winning_numbers.append(formatted_num)
                except ValueError:
                    flash(f'Advertencia: El número "{num}" no es un formato de número válido y fue ignorado.', 'warning')
                    
            if not winning_numbers:
                flash('No se pudieron procesar números ganadores válidos.', 'danger')
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))
            
            # 1. Serializar la lista de ganadores a JSON string
            winning_numbers_json = json.dumps(winning_numbers)
            
            # 2. Actualizar la tabla raffle
            db.execute("""
                UPDATE raffle SET winning_numbers = ? WHERE id = ?
            """, (winning_numbers_json, raffle_id))
            
            db.commit()
            
            # 3. Mensaje de éxito
            flash(f'Ganador(es) anunciado(s) exitosamente: {", ".join(winning_numbers)}.', 'success')
            
            # Redirigir al detalle de la rifa para ver el mensaje de ganador
            return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))
        
    except Exception as e:
        flash(f'Error al guardar/eliminar el(los) ganador(es): {e}', 'danger')
    finally:
        db.close()
        
    return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

# --- RUTA NUEVA: GENERAR TXT (Reemplaza PDF) ---
@bp.route('/rifas/reporte-txt/<int:raffle_id>')
@login_required
def generar_reporte_txt(raffle_id):
    """Superuser: Genera un archivo de texto (.txt) con el listado de números vendidos, nombre del cliente y estado de cancelación."""
    if not current_user.is_superuser():
        flash('Acceso denegado. Solo superusuarios pueden generar reportes.', 'danger')
        return redirect(url_for('rifas.ver_rifas'))

    db = get_db()
    
    # 1. Obtener información de la rifa
    raffle_data = db.execute('SELECT * FROM raffle WHERE id = ?', (raffle_id,)).fetchone()
    if not raffle_data:
        db.close()
        flash('Rifa no encontrada para generar el reporte.', 'danger')
        return redirect(url_for('rifas.ver_rifas'))
    
    # 2. Obtener todas las selecciones
    # Mantenemos las columnas para generar el reporte con los datos que ya existen en la DB
    selections = db.execute("""
        SELECT 
            customer_name, 
            number, 
            is_canceled,
            payment_method,
            sinpe_name,
            sinpe_phone
        FROM selection 
        WHERE raffle_id = ? 
        ORDER BY number ASC
    """, (raffle_id,)).fetchall()
    
    db.close()

    # --- Generación del contenido TXT ---
    try:
        reporte = []
        
        # Encabezado
        reporte.append("=" * 100)
        reporte.append(f"REPORTE DE RIFA: {raffle_data['name']}")
        reporte.append(f"Rifa #: {raffle_data['raffle_number']}")
        reporte.append(f"Premio: {raffle_data['prize']}")
        reporte.append(f"Fecha del Sorteo: {raffle_data['raffle_date']} {raffle_data['raffle_time'] or ''}")
        reporte.append(f"Precio por número: \u20a1{raffle_data['price']:.2f}")
        reporte.append("=" * 100)
        reporte.append("")
        
        # Encabezados de la tabla
        # MODIFICACIÓN: Eliminamos "PAGO" y "SINPE RECIBE" del encabezado si ya no se usan
        reporte.append(f"{'NÚMERO':<10}{'CLIENTE':<60}{'ESTADO':<15}")
        reporte.append("-" * 100)
        
        # Contenido de la tabla
        for row in selections:
            number = row['number']
            customer_name = row['customer_name']
            payment_method = row['payment_method']
            sinpe_name = row['sinpe_name'] or '' 
            sinpe_phone = row['sinpe_phone'] or ''
            is_canceled = row['is_canceled']
            
            estado = 'CANCELADO' if is_canceled else 'PENDIENTE / ACTIVO'
            # Mantenemos la lógica para incluir info de pago en el nombre si existe, aunque ya no se pide
            # En este caso, solo mostramos el nombre del cliente y el estado
            
            # Formato de la fila (alineación de texto)
            line = f"{number:<10}{customer_name[:58]:<60}{estado:<15}"
            reporte.append(line)
            
        reporte.append("-" * 100)
        reporte.append(f"Total de números vendidos/ocupados: {len(selections)}")
        reporte.append("=" * 100)
        
        txt_content = "\n".join(reporte)
        
        # Retornar la respuesta HTTP como TXT
        filename = f"reporte_rifa_{raffle_data['raffle_number']}.txt"
        response = Response(
            txt_content, 
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )
        return response

    except Exception as e:
        flash(f'Error al generar el archivo de texto: {e}', 'danger')
        return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))


# --- Rutas de Detalle y Selección de Números (Mantenidas) ---

@bp.route('/rifas/<int:raffle_id>', methods=['GET', 'POST'])
def detalle_rifa(raffle_id):
    """Vista para detalle de rifa y selección/compra de números."""
    db = get_db()
    # MODIFICACIÓN: Traemos las nuevas columnas de Sinpe por defecto
    rifa = db.execute('SELECT *, sinpe_name_default, sinpe_phone_default FROM raffle WHERE id = ?', (raffle_id,)).fetchone()
    
    if rifa is None:
        db.close()
        flash('Rifa no encontrada.', 'danger')
        return redirect(url_for('rifas.ver_rifas'))
    
    # Procesar rifa_dict y winning_numbers
    rifa_dict = dict(rifa)
    try:
        rifa_dict['winning_numbers'] = json.loads(rifa_dict['winning_numbers'])
    except (json.JSONDecodeError, TypeError):
        rifa_dict['winning_numbers'] = []
        
    # Obtener todas las selecciones (vendidas/reservadas)
    # MODIFICACIÓN: Incluimos las nuevas columnas de PAGO DEL CLIENTE
    selections = db.execute('SELECT id, raffle_id, number, customer_name, customer_phone, selection_password_hash, created_at, is_canceled, payment_method, sinpe_name, sinpe_phone FROM selection WHERE raffle_id = ?', (raffle_id,)).fetchall()
    
    # Mapeo de números seleccionados
    sold_numbers = {s['number']: dict(s) for s in selections}
    
    # 1. Lógica para manejar la selección (AJAX en el front-end)
    if request.method == 'POST':
        action = request.form.get('action')
        
        # Las acciones que requieren IDs de selección usan esta lógica común
        selection_ids_str = request.form.get('selection_ids') 
        password_check = request.form.get('edit_password')
        
        # --- Lógica de Agregar Selección ---
        if action == 'add_selection':
            name = request.form.get('customer_name')
            phone = request.form.get('customer_phone')
            password = request.form.get('selection_password')
            numbers_str = request.form.get('selected_numbers') # "01, 15, 99"
            
            # ELIMINAMOS RECOLECCIÓN DE CAMPOS DE PAGO DEL CLIENTE DEL FORMULARIO
            payment_method = 'Efectivo/Otro' # Valor por defecto
            sinpe_name = None # Valor por defecto
            sinpe_phone = None # Valor por defecto
            
            # Validación simple de campos obligatorios
            if not name or not phone or not password or not numbers_str: # Eliminamos validación de payment_method
                flash('Todos los campos de cliente y contraseña son obligatorios para la selección.', 'danger')
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))
            
            # ELIMINAMOS VALIDACIÓN ESPECÍFICA DE SINPE
            # if payment_method == 'Sinpe' and (not sinpe_name or not sinpe_phone): ...

            selected_numbers = [n.strip() for n in numbers_str.split(',')]
            password_hash = generate_password_hash(password)

            newly_selected = []
            
            try:
                for number in selected_numbers:
                    # Verificar si ya está vendido
                    existing = db.execute('SELECT * FROM selection WHERE raffle_id = ? AND number = ?', (raffle_id, number)).fetchone()
                    if existing is None:
                        # Asegurar que insertamos is_canceled = 0 por defecto
                        # MODIFICACIÓN: AÑADIR CAMPOS DE PAGO CON VALORES POR DEFECTO
                        db.execute("""
                            INSERT INTO selection (raffle_id, number, customer_name, customer_phone, selection_password_hash, is_canceled, payment_method, sinpe_name, sinpe_phone)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (raffle_id, number, name, phone, password_hash, 0, payment_method, sinpe_name, sinpe_phone))
                        newly_selected.append(number)
                
                db.commit()
                db.close()
                if newly_selected:
                    flash(f'Números {", ".join(newly_selected)} seleccionados exitosamente. Use su contraseña para editar.', 'success')
                else:
                    flash('Todos los números seleccionados ya estaban ocupados.', 'warning')
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

            except Exception as e:
                db.close()
                flash(f'Error al guardar la selección: {e}', 'danger')
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

        # --- Lógica para Editar/Eliminar/Cancelar ---
        elif action in ['edit_selection', 'delete_selection', 'cancel_selection']:
            
            if not selection_ids_str:
                flash('Error: No se proporcionaron IDs de selección.', 'danger')
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

            selection_ids = tuple(selection_ids_str.split(','))
            
            # Obtener el hash de la contraseña del primer ID para verificar
            first_selection_id = selection_ids[0]
            selection_to_check = db.execute('SELECT selection_password_hash FROM selection WHERE id = ?', (first_selection_id,)).fetchone()
            
            if not selection_to_check:
                flash('Error: Selección no encontrada o IDs inválidos.', 'danger')
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

            # --- VERIFICACIÓN DE PERMISOS/CONTRASEÑA ---
            password_ok = False
            
            # Regla de Superusuario: Si es Superusuario, la contraseña es opcional
            if current_user.is_authenticated and current_user.is_superuser():
                password_ok = True
            
            # Regla de Usuario Normal: Debe ingresar la contraseña correcta
            if not password_ok and password_check:
                if check_password_hash(selection_to_check['selection_password_hash'], password_check):
                    password_ok = True
            
            if not password_ok:
                flash('Contraseña de edición incorrecta o faltante.', 'danger')
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))
            
            # --- Proceso de Acciones ---
            placeholders = ','.join('?' * len(selection_ids))
            
            try: # Agregamos un try/finally aquí también
                if action == 'delete_selection':
                    # MODIFICACIÓN: Agregamos las nuevas columnas a la sentencia DELETE
                    db.execute(f'DELETE FROM selection WHERE id IN ({placeholders})', selection_ids)
                    db.commit()
                    flash(f'Los números han sido liberados y eliminados.', 'success')
                
                elif action == 'cancel_selection':
                    # MODIFICACIÓN: Solo superusuarios pueden cancelar, ya revisado arriba.
                    if not current_user.is_superuser():
                        flash('Acción denegada. Solo superusuarios pueden cancelar selecciones.', 'danger')
                        return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))
                        
                    # Marcamos como cancelado (1)
                    db.execute(f'UPDATE selection SET is_canceled = 1 WHERE id IN ({placeholders})', selection_ids)
                    db.commit()
                    flash('La selección ha sido marcada como CANCELADA. El card se ha puesto verde.', 'success')
                
                elif action == 'edit_selection':
                    flash('Funcionalidad de Edición de Cliente no implementada aún.', 'info')
            except Exception as e:
                db.rollback()
                flash(f'Error al realizar la acción {action}: {e}', 'danger')
            finally:
                db.close()
                
            return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))


    db.close()
    return render_template(
        'detalle_rifa.html', 
        title=f'Detalle de Rifa: {rifa_dict["name"]}', 
        rifa=rifa_dict,
        sold_numbers=sold_numbers
    )


# --- Manejo de Errores ---

@login_manager.unauthorized_handler
def unauthorized_callback():
    flash('Necesitas iniciar sesión para acceder a esta página.', 'warning')
    return redirect(url_for('rifas.login'))

@bp.teardown_request
def close_connection(exception):
    """Cierra la conexión a la DB después de cada request."""
    # Nota: Flask tiene un mecanismo para manejar esto, pero si usamos la implementación de
    # get_db() con un contexto (with app.app_context()), el cierre debe ser manual o 
    # manejado por Flask. Tu implementación actual con get_db() requiere cierres manuales 
    # en cada ruta. Mantenemos el teardown como respaldo, aunque no es estrictamente 
    # necesario si cada ruta cierra la conexión.
    db = getattr(bp, '_database', None)
    if db is not None:
        db.close()

# Esto se usará para exponer el UPLOAD_FOLDER y la función 'now_year' a Jinja para el src de las imágenes y el footer.
@bp.context_processor
def utility_processor():
    def get_image_url(filename):
        return url_for('static', filename='uploads/' + filename)
    
    # Función para obtener el año actual
    def now_year():
        return datetime.now().year
    
    # FUNCIÓN MODIFICADA: Ahora usa get_db() y busca el estado 'Cancelado' si no hay un ganador activo.
    def get_winner_info(raffle_id, winning_number):
        # ABRIMOS CONEXIÓN
        db = get_db()
        try:
            # 1. Buscamos un ganador ACTIVO (is_canceled = 0)
            winner = db.execute(
                'SELECT customer_name, customer_phone FROM selection WHERE raffle_id = ? AND number = ? AND is_canceled = 0',
                (raffle_id, winning_number)
            ).fetchone()
            
            if winner:
                # Retorna la información del ganador activo
                return dict(winner)
            
            # 2. Si no hay ganador activo, buscamos si el número fue CANCELADO (is_canceled = 1)
            canceled = db.execute(
                'SELECT customer_name, customer_phone FROM selection WHERE raffle_id = ? AND number = ? AND is_canceled = 1',
                (raffle_id, winning_number)
            ).fetchone()
            
            if canceled:
                # Retorna la información de la selección cancelada con un marcador
                info = dict(canceled)
                # Usamos una clave especial para que Jinja lo sepa
                info['status'] = 'CANCELADO'
                return info
            
            # 3. Si no hay registro activo ni cancelado (o fue eliminado)
            return {'status': 'NO_VENDIDO_O_ELIMINADO'}
            
        except Exception as e:
            # En caso de error de DB, devolvemos un marcador de error
            print(f"Error al buscar ganador para rifa {raffle_id}, número {winning_number}: {e}")
            return {'status': 'ERROR_DB'}
        finally:
            # CERRAMOS CONEXIÓN
            db.close()
        
    return dict(get_image_url=get_image_url, now_year=now_year, get_winner_info=get_winner_info)
