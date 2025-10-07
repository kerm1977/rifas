# rifas.py (Lógica del Blueprint de Rifas - Flask)
import sqlite3
import os
import secrets
import json # Necesario para manejar la lista de ganadores en JSON
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, Response
# IMPORTANTE: AHORA flask_login es el que maneja la persistencia.
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

    # MIGRACIÓN: Asegurar que las nuevas columnas existan (mantenemos esta sección por seguridad)
    try:
        db.execute("ALTER TABLE selection ADD COLUMN is_canceled BOOLEAN DEFAULT 0")
        db.commit()
    except sqlite3.OperationalError:
        pass 
        
    try:
        db.execute("ALTER TABLE raffle ADD COLUMN winning_numbers TEXT DEFAULT '[]'")
        db.commit()
    except sqlite3.OperationalError:
        pass 
        
    try:
        db.execute("ALTER TABLE raffle ADD COLUMN sinpe_name_default TEXT")
        db.execute("ALTER TABLE raffle ADD COLUMN sinpe_phone_default TEXT")
        db.commit()
    except sqlite3.OperationalError:
        pass 
        
    try:
        db.execute("ALTER TABLE selection ADD COLUMN payment_method TEXT DEFAULT 'No especificado'")
        db.execute("ALTER TABLE selection ADD COLUMN sinpe_name TEXT")
        db.execute("ALTER TABLE selection ADD COLUMN sinpe_phone TEXT")
        db.commit()
    except sqlite3.OperationalError:
        pass 

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
        remember = bool(request.form.get('remember'))
        
        db = get_db()
        user_data = db.execute('SELECT * FROM user WHERE email = ?', (email,)).fetchone()
        db.close()
        
        if user_data:
            user = User(**user_data)
            if check_password_hash(user.password_hash, password):
                
                if user.is_superuser():
                    remember = True

                login_user(user, remember=remember) 
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
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')

        if not password or len(password) < 8:
            password = secrets.token_urlsafe(8)
            flash(f"Contraseña autogenerada: {password}. Por favor, anótela.", 'info')
        
        if not confirm_password or len(confirm_password) < 8:
            confirm_password = password

        if password != confirm_password:
            flash('Las contraseñas no coinciden.', 'danger')
            return redirect(url_for('rifas.register'))

        password_hash = generate_password_hash(password)

        db = get_db()
        
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
    rifas_data = db.execute("""
        SELECT 
            r.*, 
            COUNT(s.id) as total_sold_numbers
        FROM raffle r
        LEFT JOIN selection s ON r.id = s.raffle_id AND s.is_canceled = 0
        GROUP BY r.id
        ORDER BY r.raffle_date DESC
    """).fetchall()
    db.close()
    
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
        
        payment_method_select = data.get('payment_method')
        sinpe_name_default = data.get('sinpe_name_default') if payment_method_select == 'Sinpe' else None
        sinpe_phone_default = data.get('sinpe_phone_default') if payment_method_select == 'Sinpe' else None

        if not image_file or image_file.filename == '' or not allowed_file(image_file.filename):
            flash('Debe subir una imagen válida (PNG, JPG, JPEG).', 'danger')
            return redirect(request.url)

        filename = secure_filename(image_file.filename)
        filepath = os.path.join(current_app.root_path, UPLOAD_FOLDER, filename)
        
        try:
            img = Image.open(image_file)
            if img.width > 800:
                img = img.resize((800, int(img.height * 800 / img.width)), Image.LANCZOS)
            img.save(filepath)
        except Exception as e:
            flash(f'Error al procesar la imagen: {e}', 'danger')
            return redirect(request.url)

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
                data.get('raffle_time') or None,
                filename,
                '[]',
                sinpe_name_default,
                sinpe_phone_default
            ))
            db.commit()
            db.close()
            flash('Rifa creada exitosamente.', 'success')
            return redirect(url_for('rifas.ver_rifas'))
        except sqlite3.IntegrityError:
            flash('Error: El número de rifa ya existe.', 'danger')
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
    rifa = db.execute('SELECT * FROM raffle WHERE id = ?', (raffle_id,)).fetchone()

    if rifa is None:
        db.close()
        flash('Rifa no encontrada.', 'danger')
        return redirect(url_for('rifas.ver_rifas'))
    
    rifa_dict = dict(rifa)

    if request.method == 'POST':
        data = request.form
        image_file = request.files.get('image')
        new_filename = rifa_dict['image_filename']
        filepath = None
        
        payment_method_select = data.get('payment_method')
        sinpe_name_default = data.get('sinpe_name_default') if payment_method_select == 'Sinpe' else None
        sinpe_phone_default = data.get('sinpe_phone_default') if payment_method_select == 'Sinpe' else None

        try:
            if image_file and image_file.filename != '' and allowed_file(image_file.filename):
                old_filepath = os.path.join(current_app.root_path, UPLOAD_FOLDER, rifa_dict['image_filename'])
                if os.path.exists(old_filepath):
                    os.remove(old_filepath)

                new_filename = secure_filename(image_file.filename)
                filepath = os.path.join(current_app.root_path, UPLOAD_FOLDER, new_filename)
                
                img = Image.open(image_file)
                if img.width > 800:
                    img = img.resize((800, int(img.height * 800 / img.width)), Image.LANCZOS)
                img.save(filepath)

            db.execute("""
                UPDATE raffle SET
                    raffle_number = ?, name = ?, price = ?, prize = ?, detail = ?, 
                    raffle_date = ?, raffle_time = ?, image_filename = ?,
                    sinpe_name_default = ?, sinpe_phone_default = ?
                WHERE id = ?
            """, (
                data.get('raffle_number'),
                data.get('name'),
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
            if filepath and os.path.exists(filepath):
                os.remove(filepath)
        finally:
            db.close()
    
    db.close()
    return render_template('editar_rifa.html', title=f'Editar Rifa: {rifa_dict["name"]}', rifa=rifa_dict)

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
        # Se elimina la imagen física
        image_filepath = os.path.join(current_app.root_path, UPLOAD_FOLDER, rifa['image_filename'])
        if os.path.exists(image_filepath):
            os.remove(image_filepath)

        # Se eliminan los números seleccionados (Foreign Key cascade no está activo, así que se hace manualmente)
        db.execute('DELETE FROM selection WHERE raffle_id = ?', (raffle_id,))
        # Se elimina la rifa
        db.execute('DELETE FROM raffle WHERE id = ?', (raffle_id,))
        
        db.commit()
        flash('Rifa eliminada permanentemente, incluyendo todos sus números vendidos.', 'success')
        
    except Exception as e:
        db.rollback() 
        flash(f'Error al eliminar la rifa: {e}', 'danger')
        
    finally:
        db.close()
        
    return redirect(url_for('rifas.ver_rifas'))


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
            db.execute("UPDATE raffle SET winning_numbers = '[]' WHERE id = ?", (raffle_id,))
            db.commit()
            flash('¡Ganadores eliminados! La rifa ha sido reseteada.', 'success')
            return redirect(url_for('rifas.ver_rifas')) 
            
        else:
            numbers_str = request.form.get('winning_numbers')
            
            if not numbers_str:
                flash('Debe seleccionar al menos un número ganador.', 'danger')
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

            raw_numbers = [n.strip() for n in numbers_str.split(',') if n.strip()]
            winning_numbers = []
            
            for num in raw_numbers:
                try:
                    formatted_num = f"{int(num):02d}" 
                    winning_numbers.append(formatted_num)
                except ValueError:
                    flash(f'Advertencia: El número "{num}" no es un formato de número válido y fue ignorado.', 'warning')
                    
            if not winning_numbers:
                flash('No se pudieron procesar números ganadores válidos.', 'danger')
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))
            
            winning_numbers_json = json.dumps(winning_numbers)
            db.execute("UPDATE raffle SET winning_numbers = ? WHERE id = ?", (winning_numbers_json, raffle_id))
            db.commit()
            flash(f'Ganador(es) anunciado(s) exitosamente: {", ".join(winning_numbers)}.', 'success')
            return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))
        
    except Exception as e:
        flash(f'Error al guardar/eliminar el(los) ganador(es): {e}', 'danger')
    finally:
        db.close()
        
    return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

@bp.route('/rifas/reporte-txt/<int:raffle_id>')
@login_required
def generar_reporte_txt(raffle_id):
    """Superuser: Genera un archivo de texto (.txt) con el listado de números vendidos."""
    if not current_user.is_superuser():
        flash('Acceso denegado. Solo superusuarios pueden generar reportes.', 'danger')
        return redirect(url_for('rifas.ver_rifas'))

    db = get_db()
    
    raffle_data = db.execute('SELECT * FROM raffle WHERE id = ?', (raffle_id,)).fetchone()
    if not raffle_data:
        db.close()
        flash('Rifa no encontrada para generar el reporte.', 'danger')
        return redirect(url_for('rifas.ver_rifas'))
    
    selections = db.execute("""
        SELECT customer_name, number, is_canceled
        FROM selection 
        WHERE raffle_id = ? 
        ORDER BY number ASC
    """, (raffle_id,)).fetchall()
    
    db.close()

    try:
        reporte = []
        reporte.append("=" * 80)
        reporte.append(f"REPORTE DE RIFA: {raffle_data['name']} (#{raffle_data['raffle_number']})")
        reporte.append(f"Fecha del Sorteo: {raffle_data['raffle_date']}")
        reporte.append("=" * 80)
        reporte.append(f"{'NÚMERO':<10}{'CLIENTE':<50}{'ESTADO':<15}")
        reporte.append("-" * 80)
        
        for row in selections:
            # is_canceled = 1 indica CANCELADO
            estado = 'CANCELADO' if row['is_canceled'] else 'ACTIVO'
            line = f"{row['number']:<10}{row['customer_name'][:48]:<50}{estado:<15}"
            reporte.append(line)
            
        reporte.append("-" * 80)
        
        # Conteo de activos y cancelados
        total_activos = sum(1 for s in selections if s['is_canceled'] == 0)
        total_cancelados = len(selections) - total_activos
        
        reporte.append(f"Total de números activos: {total_activos}")
        reporte.append(f"Total de números cancelados: {total_cancelados}")
        reporte.append(f"Total de números ocupados (Activos + Cancelados): {len(selections)}")

        reporte.append("=" * 80)
        
        txt_content = "\n".join(reporte)
        
        filename = f"reporte_rifa_{raffle_data['raffle_number']}.txt"
        return Response(
            txt_content, 
            mimetype='text/plain',
            headers={'Content-Disposition': f'attachment;filename={filename}'}
        )

    except Exception as e:
        flash(f'Error al generar el archivo de texto: {e}', 'danger')
        return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))


@bp.route('/rifas/<int:raffle_id>', methods=['GET', 'POST'])
def detalle_rifa(raffle_id):
    """
    Vista para detalle de rifa y selección/compra de números.
    Maneja la acción POST de compra/selección y ahora la eliminación por contraseña.
    """
    db = get_db()
    rifa = db.execute('SELECT *, sinpe_name_default, sinpe_phone_default FROM raffle WHERE id = ?', (raffle_id,)).fetchone()
    
    if rifa is None:
        db.close()
        flash('Rifa no encontrada.', 'danger')
        return redirect(url_for('rifas.ver_rifas'))
    
    rifa_dict = dict(rifa)
    try:
        rifa_dict['winning_numbers'] = json.loads(rifa_dict['winning_numbers'])
    except (json.JSONDecodeError, TypeError):
        rifa_dict['winning_numbers'] = []
        
    selections = db.execute('SELECT * FROM selection WHERE raffle_id = ?', (raffle_id,)).fetchall()
    
    # --- Agrupación de selecciones ---
    grouped_selections = {}
    total_numbers_occupied = len(selections) 
    
    for selection in selections:
        # Usamos el customer_phone como clave principal para agrupar, ya que es único.
        customer_key = selection['customer_phone'] 
        
        if customer_key not in grouped_selections:
            grouped_selections[customer_key] = {
                'customer_name': selection['customer_name'],
                'customer_phone': selection['customer_phone'],
                'created_at': selection['created_at'],
                'numbers': [],
                'selection_ids': [],
                'is_canceled': selection['is_canceled'],
                'payment_method': selection['payment_method'],
                'sinpe_name': selection['sinpe_name'],
                'sinpe_phone': selection['sinpe_phone']
            }
        
        grouped_selections[customer_key]['numbers'].append(selection['number'])
        grouped_selections[customer_key]['selection_ids'].append(selection['id'])
        grouped_selections[customer_key]['is_canceled'] = selection['is_canceled']


    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'add_selection':
            name = request.form.get('customer_name')
            phone = request.form.get('customer_phone')
            password = request.form.get('selection_password')
            numbers_str = request.form.get('selected_numbers')
            
            payment_method = 'No especificado'
            sinpe_name = None
            sinpe_phone = None
            
            if not name or not phone or not password or not numbers_str:
                flash('Todos los campos de cliente y contraseña son obligatorios.', 'danger')
                db.close()
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

            selected_numbers = [n.strip() for n in numbers_str.split(',') if n.strip()]
            
            if not selected_numbers:
                flash('No se seleccionaron números válidos.', 'danger')
                db.close()
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

            password_hash = generate_password_hash(password)
            newly_selected = []
            
            try:
                for number in selected_numbers:
                    # Validar si el número ya está ocupado (activo o cancelado)
                    formatted_number = f"{int(number):02d}" # Asegurar formato 00
                    existing = db.execute('SELECT id FROM selection WHERE raffle_id = ? AND number = ?', (raffle_id, formatted_number)).fetchone()
                    
                    if existing is None:
                        db.execute("""
                            INSERT INTO selection (raffle_id, number, customer_name, customer_phone, selection_password_hash, is_canceled, payment_method, sinpe_name, sinpe_phone)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (raffle_id, formatted_number, name, phone, password_hash, 0, payment_method, sinpe_name, sinpe_phone))
                        
                        newly_selected.append(formatted_number)
                    else:
                        flash(f'El número {number} ya estaba ocupado y fue omitido.', 'warning')
                
                db.commit()
                if newly_selected:
                    flash(f'Números {", ".join(newly_selected)} seleccionados exitosamente y protegidos con contraseña.', 'success')
                
            except Exception as e:
                db.rollback()
                flash(f'Error al guardar la selección: {e}', 'danger')
            finally:
                db.close()
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

        elif action == 'delete_selection':
            password_check = request.form.get('delete_password')
            selection_ids_str = request.form.get('selection_ids')
            
            if not password_check or not selection_ids_str:
                flash('Faltan datos (Contraseña o IDs de selección).', 'danger')
                db.close()
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

            selection_ids = tuple(selection_ids_str.split(','))
            
            # 1. Obtener el hash de contraseña de la primera selección para verificación
            first_selection = db.execute('SELECT selection_password_hash FROM selection WHERE id = ?', (selection_ids[0],)).fetchone()
            
            if not first_selection:
                flash('Error: Selección no encontrada.', 'danger')
                db.close()
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

            # 2. Verificar la contraseña
            if not check_password_hash(first_selection['selection_password_hash'], password_check):
                flash('Contraseña de protección incorrecta. No se liberaron los números.', 'danger')
                db.close()
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))
            
            # 3. Eliminar (Liberar) los números
            placeholders = ','.join('?' * len(selection_ids))
            
            try:
                db.execute(f'DELETE FROM selection WHERE id IN ({placeholders})', selection_ids)
                db.commit()
                flash('¡Números liberados exitosamente! Ya están disponibles para compra.', 'success')
            except Exception as e:
                db.rollback()
                flash(f'Error al liberar la selección: {e}', 'danger')
            finally:
                db.close()
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

        # Reintroducir la lógica de Marcar Cancelado (Solo Superusuario)
        elif action == 'mark_canceled' and current_user.is_authenticated and current_user.is_superuser():
            selection_ids_str = request.form.get('selection_ids')
            if not selection_ids_str:
                flash('Error: No se proporcionaron IDs para cancelar.', 'danger')
                db.close()
                return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))

            selection_ids = tuple(selection_ids_str.split(','))
            placeholders = ','.join('?' * len(selection_ids))

            try:
                # Marcar como cancelado (1)
                db.execute(f'UPDATE selection SET is_canceled = 1 WHERE id IN ({placeholders})', selection_ids)
                db.commit()
                flash('La selección ha sido marcada como CANCELADA (Admin).', 'warning')
            except Exception as e:
                db.rollback()
                flash(f'Error al cancelar la selección: {e}', 'danger')
            finally:
                db.close()
            
            return redirect(url_for('rifas.detalle_rifa', raffle_id=raffle_id))
            
        # El resto de acciones POST (si las hubiera)
        
    db.close()
    return render_template(
        'detalle_rifa.html', 
        title=f'Detalle de Rifa: {rifa_dict["name"]}', 
        rifa=rifa_dict,
        sold_numbers= {s['number']: dict(s) for s in selections},
        grouped_selections=grouped_selections, # Pasamos los datos ya agrupados
        total_numbers_occupied=total_numbers_occupied # Pasamos el conteo
    )

@login_manager.unauthorized_handler
def unauthorized_callback():
    flash('Necesitas iniciar sesión para acceder a esta página.', 'warning')
    return redirect(url_for('rifas.login'))

@bp.teardown_request
def close_connection(exception):
    db = getattr(bp, '_database', None)
    if db is not None:
        db.close()

@bp.context_processor
def utility_processor():
    def get_image_url(filename):
        return url_for('static', filename='uploads/' + filename)
    
    def now_year():
        return datetime.now().year
    
    def get_winner_info(raffle_id, winning_number):
        db = get_db()
        try:
            # Buscar número ACTIVO
            winner = db.execute(
                'SELECT customer_name, customer_phone FROM selection WHERE raffle_id = ? AND number = ? AND is_canceled = 0',
                (raffle_id, winning_number)
            ).fetchone()
            
            if winner:
                return dict(winner)
            
            # Buscar número CANCELADO
            canceled = db.execute(
                'SELECT customer_name, customer_phone FROM selection WHERE raffle_id = ? AND number = ? AND is_canceled = 1',
                (raffle_id, winning_number)
            ).fetchone()
            
            if canceled:
                info = dict(canceled)
                info['status'] = 'CANCELADO'
                return info
            
            return {'status': 'NO_VENDIDO_O_ELIMINADO'}
            
        except Exception as e:
            print(f"Error al buscar ganador para rifa {raffle_id}, número {winning_number}: {e}")
            return {'status': 'ERROR_DB'}
        finally:
            db.close()
        
    return dict(get_image_url=get_image_url, now_year=now_year, get_winner_info=get_winner_info)
