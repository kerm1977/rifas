import os
import mimetypes
import string
import sqlite3
import json
from pathlib import Path
from flask import Blueprint, render_template, current_app, send_file, request, Response, flash, redirect, url_for
from werkzeug.security import safe_join
from flask_login import login_required, current_user 

# Definición del Blueprint
bp = Blueprint('movies', __name__, template_folder='templates', url_prefix='/streaming')

# ==============================================================================
# CONFIGURACIÓN Y UTILIDADES DE DB
# ==============================================================================

# Extensiónes de archivo soportadas
SUPPORTED_EXTENSIONS = ('.mp4', '.webm', '.mkv', '.avi', '.mov', '.flv')

def get_db():
    """Establece la conexión a la base de datos."""
    # Reutiliza la configuración de la DB principal del proyecto (rifas.sqlite)
    db = sqlite3.connect(current_app.config['DATABASE'], detect_types=sqlite3.PARSE_DECLTYPES)
    db.row_factory = sqlite3.Row
    return db

def init_movie_db():
    """Crea la tabla de videos escaneados si no existe."""
    db = get_db()
    # Guardamos el ID del usuario para que cada usuario tenga su propia lista de videos
    # El usuario '0' se puede usar para videos públicos si se desea.
    db.execute("""
        CREATE TABLE IF NOT EXISTS scanned_videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            filename_id TEXT UNIQUE NOT NULL, -- Ruta codificada (usada como ID)
            title TEXT NOT NULL,
            display_path TEXT,
            UNIQUE (user_id, filename_id)
        );
    """)
    db.commit()
    db.close()

# ==============================================================================
# LÓGICA DE ESCANEO Y RUTAS DE DISCO (Mejorada para Windows/Posix)
# ==============================================================================

def get_available_scan_options(root_path):
    """
    Genera una lista de rutas comunes para usar en el selector (SELECT/OPTION).
    Devuelve: [{label: "C: (Disco Local)", path: "C:\\"}, ...]
    """
    options = []
    
    # 1. Carpeta local del proyecto (siempre incluida)
    local_path = str(Path(root_path) / 'videos')
    # Usar os.path.normpath para normalizar la ruta
    options.append({'label': "Carpeta local del proyecto (/videos)", 'path': os.path.normpath(local_path)})

    # 2. Unidades de disco de Windows (C: a Z:) y rutas comunes
    if os.name == 'nt': 
        # Generar unidades C: a Z:
        for letter in string.ascii_uppercase:
            drive_path = f"{letter}:\\"
            if Path(drive_path).exists():
                options.append({'label': f"Unidad {letter}: (Disco/Tarjeta/Móvil)", 'path': drive_path})
        
        # Rutas comunes para directorios de usuarios en Windows (ej. Videos, Descargas)
        try:
            home = str(Path.home())
            options.append({'label': f"Videos del Usuario ({os.path.basename(home)})", 'path': os.path.normpath(os.path.join(home, 'Videos'))})
            options.append({'label': f"Descargas del Usuario ({os.path.basename(home)})", 'path': os.path.normpath(os.path.join(home, 'Downloads'))})
            options.append({'label': f"Documentos del Usuario ({os.path.basename(home)})", 'path': os.path.normpath(os.path.join(home, 'Documents'))})
        except:
            pass 

    # 3. Rutas comunes de montaje en Linux/macOS
    elif os.name == 'posix': 
        # Puntos de montaje comunes para discos externos
        options.append({'label': "Puntos de Montaje (/media /Volumes)", 'path': os.path.normpath('/')})
        options.append({'label': "Punto de Montaje de Discos USB (/media)", 'path': os.path.normpath('/media')})
        options.append({'label': "Punto de Montaje de Discos USB (/mnt)", 'path': os.path.normpath('/mnt')})
        options.append({'label': "Discos de macOS (/Volumes)", 'path': os.path.normpath('/Volumes')})

        try:
            home = str(Path.home())
            options.append({'label': f"Videos del Usuario ({os.path.basename(home)})", 'path': os.path.normpath(os.path.join(home, 'Movies'))})
            options.append({'label': f"Descargas del Usuario ({os.path.basename(home)})", 'path': os.path.normpath(os.path.join(home, 'Downloads'))})
        except:
            pass
                
    return options

def perform_scan(user_id, scan_path):
    """
    Realiza el escaneo recursivo en una ruta específica y guarda los resultados en DB.
    """
    if not scan_path:
        return 0, "Error: Ruta de escaneo no especificada."

    scan_path_obj = Path(scan_path)
    # 1. Validación de existencia
    if not scan_path_obj.is_dir():
        return 0, f"Error: La ruta '{scan_path}' no existe o no es un directorio. Asegúrate de que el disco esté conectado y montado."

    db = get_db()
    count = 0
    
    try:
        # Usamos os.walk para iterar de forma eficiente
        for root, _, files in os.walk(scan_path_obj):
            for file in files:
                if file.lower().endswith(SUPPORTED_EXTENSIONS):
                    full_path = Path(root) / file
                    
                    # Generar ID (ruta codificada)
                    # Reemplazamos ':' y '/' por cadenas seguras para usar como ID en la URL
                    encoded_path = str(full_path).replace('\\', '/').replace(':', '_COLON_') 
                    
                    # 2. Preparar metadatos
                    title = Path(file).stem.replace('.', ' ').title()
                    
                    # Ruta visible (acortada si es muy larga)
                    try:
                        # Intentamos mostrar la ruta relativa para que sea más corta
                        display_path = str(full_path.relative_to(scan_path_obj))
                    except ValueError:
                        # Si no es un subdirectorio, usamos la ruta completa
                        display_path = str(full_path)
                    
                    if len(display_path) > 70:
                        display_path = '... ' + display_path[-67:]

                    # 3. Insertar o reemplazar el video en la DB
                    # 'INSERT OR REPLACE' asegura que si escaneamos dos veces, no haya duplicados.
                    db.execute("""
                        INSERT OR REPLACE INTO scanned_videos 
                        (user_id, filename_id, title, display_path)
                        VALUES (?, ?, ?, ?)
                    """, (user_id, encoded_path, title, display_path))
                    count += 1
        
        db.commit()
        return count, f"Escaneo exitoso. {count} videos encontrados y añadidos."
        
    except PermissionError:
        return 0, f"Error de Permiso: No se pudo acceder a la ruta: {scan_path}. Asegúrate de tener permisos de lectura."
    except Exception as e:
        db.rollback()
        return 0, f"Error inesperado durante el escaneo de {scan_path}: {e}."
    finally:
        db.close()


# ==============================================================================
# LÓGICA DE STREAMING (Byte Serving)
# ==============================================================================

# Tamaño de los chunks a enviar al cliente (64 KB)
CHUNK_SIZE = 65536

def stream_video(video_path):
    """
    Implementa la lógica de Byte Serving usando encabezados Range para streaming.
    """
    # ... [función stream_video sin cambios, ya es funcional]
    file_size = os.stat(video_path).st_size
    range_header = request.headers.get('Range', None)

    if not range_header:
        headers = {
            'Content-Type': mimetypes.guess_type(video_path)[0] or 'video/mp4',
            'Content-Length': file_size,
            'Accept-Ranges': 'bytes'
        }
        return Response(
            open(video_path, 'rb').read(), 
            status=200, 
            headers=headers
        )

    try:
        byte_range = range_header.split('=')[1]
        start, end = byte_range.split('-')
        
        start = int(start)
        end = int(end) if end else min(start + CHUNK_SIZE, file_size - 1)
        end = min(end, file_size - 1)
        
    except Exception as e:
        print(f"Error al parsear Range header: {e}")
        return Response(status=400) 

    length = end - start + 1
    
    with open(video_path, 'rb') as f:
        f.seek(start)
        data = f.read(length)

    headers = {
        'Content-Type': mimetypes.guess_type(video_path)[0] or 'video/mp4',
        'Content-Length': length,
        'Content-Range': f'bytes {start}-{end}/{file_size}',
        'Accept-Ranges': 'bytes'
    }

    return Response(
        data,
        status=206, # Código de respuesta: Contenido Parcial
        headers=headers
    )

# ==============================================================================
# RUTAS DE LA APLICACIÓN
# ==============================================================================

@bp.route('/', methods=['GET'])
@login_required
def browse_files():
    """Muestra la interfaz tipo Netflix con la lista de videos desde la DB."""
    
    # 1. Obtener opciones de escaneo para el selector
    # Estas opciones incluyen todas las unidades C: a Z: y rutas comunes de montaje.
    scan_options = get_available_scan_options(current_app.root_path)

    # 2. Obtener videos ALMACENADOS en la DB para el usuario actual
    user_id = str(current_user.id)
    db = get_db()
    
    # Consultar todos los videos escaneados por este usuario
    videos_data = db.execute('SELECT filename_id, title, display_path FROM scanned_videos WHERE user_id = ?', (user_id,)).fetchall()
    db.close()
    
    videos = [dict(v) for v in videos_data]

    # Si eres superusuario, tienes acceso total
    is_superuser = current_user.is_authenticated and current_user.is_superuser()
            
    return render_template(
        'movies.html', 
        title='Mi Video Streaming Casero', 
        videos=videos,
        is_superuser=is_superuser,
        scan_options=scan_options
    )

@bp.route('/scan', methods=['POST'])
@login_required
def start_scan():
    """Ruta para iniciar el escaneo manual de un directorio."""
    scan_path = request.form.get('scan_path')
    user_id = str(current_user.id)
    
    if not scan_path:
        flash('Error: Debe seleccionar un directorio para escanear.', 'danger')
        return redirect(url_for('movies.browse_files'))
        
    # Eliminar barras diagonales finales innecesarias para la normalización de Path
    scan_path_normalized = os.path.normpath(scan_path)
        
    count, message = perform_scan(user_id, scan_path_normalized)
    
    # Usar el tipo de flash adecuado basado en el resultado
    if count > 0 and "Error" not in message:
        flash(message, 'success')
    else:
        # Añadimos un mensaje claro de que no se encontraron videos
        if count == 0 and "Error" not in message:
             flash(f"Escaneo completado. No se encontraron archivos de video válidos en: {scan_path_normalized}", 'info')
        else:
             flash(message, 'warning')
        
    return redirect(url_for('movies.browse_files'))


@bp.route('/clear_scan', methods=['POST'])
@login_required
def clear_scan():
    """Ruta para borrar la lista de videos escaneados del usuario."""
    user_id = str(current_user.id)
    db = get_db()
    try:
        db.execute('DELETE FROM scanned_videos WHERE user_id = ?', (user_id,))
        db.commit()
        flash('Catálogo de videos borrado exitosamente. Escanee una nueva ubicación.', 'success')
    except Exception as e:
        db.rollback()
        flash(f'Error al borrar el catálogo: {e}', 'danger')
    finally:
        db.close()
        
    return redirect(url_for('movies.browse_files'))


@bp.route('/play/<filename_id>', methods=['GET'])
@login_required 
def play_video(filename_id):
    """Ruta para reproducir un video específico usando Byte Serving."""
    
    # 1. Descodificar el ID de vuelta a la ruta completa
    decoded_path = filename_id.replace('_COLON_', ':').replace('/', os.sep)
    video_file = Path(decoded_path)
    
    # 2. Verificación de Seguridad: Asegurar que el archivo exista y sea un archivo
    if not video_file.is_file():
        # Antes de fallar, verificamos si es un video de un escaneo anterior
        # y si el disco está ahora desconectado, para dar un mensaje más claro.
        db = get_db()
        video_data = db.execute('SELECT display_path FROM scanned_videos WHERE filename_id = ?', (filename_id,)).fetchone()
        db.close()
        
        message = f"Error 404: Video no encontrado en la ruta: {video_file}."
        if video_data:
            message += " (El disco duro o dispositivo móvil podría estar desconectado. Intente escanear de nuevo)."
            
        return message, 404

    # 3. Servir el video usando la función de streaming
    return stream_video(str(video_file))
