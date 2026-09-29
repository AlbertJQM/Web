from flask import Flask, render_template, request, url_for, redirect, session, flash, get_flashed_messages, jsonify
from config import Config
from models import db, Usuario, Tarea
from datetime import datetime
from functools import wraps

app = Flask(__name__)
#Configuración de la aplicación Flask (donde se indica la base de datos a usar)
app.config.from_object(Config)

# Inicializar la base de datos
db.init_app(app)
# Crear la base de datos si no existe
with app.app_context():
    db.create_all()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if "usuario_id" in session:
        return redirect(url_for("list_tasks"))
    if request.method == 'POST':
        correo = request.form['correo']
        contrasena = request.form['contrasena']
        
        usuario = Usuario.query.filter_by(correo=correo).first()
        if usuario and usuario.verificar_contrasena(contrasena):
            session["usuario_id"] = usuario.id
            session["usuario_nombre"] = usuario.nombre
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('list_tasks'))
        else:
            flash('Correo o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión exitosamente.', 'info')
    return redirect(url_for('home'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        nombre = request.form['nombre']
        correo = request.form['correo']
        contrasena = request.form['contrasena']
        if Usuario.query.filter_by(correo=correo).first():
            flash('El correo ya está registrado.', 'warning')
        else:
            nuevo_usuario = Usuario(nombre=nombre, correo=correo)
            nuevo_usuario.colocar_contrasena(contrasena)
            db.session.add(nuevo_usuario)
            db.session.commit()
            flash('Usuario registrado exitosamente.', 'success')
            return redirect(url_for('login'))
    return render_template('signup.html')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "usuario_id" not in session:
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/tasks')
@login_required
def list_tasks():
    usuario_id = session.get('usuario_id')
    estado = request.args.get('estado', "todas")
    
    total_tareas = Tarea.query.filter_by(usuario_id=usuario_id).count()
    pendientes = Tarea.query.filter_by(usuario_id=usuario_id, completada=False).count()
    completadas = Tarea.query.filter_by(usuario_id=usuario_id, completada=True).count()
    
    if estado == 'pendientes':
        tareas = Tarea.query.filter_by(usuario_id=usuario_id, completada=False).all()
    elif estado == 'completadas':
        tareas = Tarea.query.filter_by(usuario_id=usuario_id, completada=True).all()
    else:
        tareas = Tarea.query.filter_by(usuario_id=usuario_id).all()

    return render_template('tasks.html', tareas=tareas, total_tareas=total_tareas, pendientes=pendientes, completadas=completadas, estado=estado)

@app.route('/task/<int:id>')
@login_required
def view_task(id):
    tarea = Tarea.query.get_or_404(id)
    return render_template('task.html', tarea=tarea)

@app.route('/task/create', methods=['GET', 'POST'])
@login_required
def create_task():
    if request.method == 'POST':
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        fecha_vencimiento = datetime.strptime(request.form['fecha'], '%Y-%m-%d')
        prioridad = request.form['prioridad']
        try:
            nueva_tarea = Tarea(titulo=titulo, descripcion=descripcion, fecha_vencimiento=fecha_vencimiento, prioridad=prioridad, usuario_id=session['usuario_id'])
            db.session.add(nueva_tarea)
            db.session.commit()
            flash('Tarea agregada exitosamente.', 'success')
            return redirect(url_for('list_tasks'))
        except Exception as e:
            flash('Error al crear la tarea.', 'danger')
            return f"Error al crear la tarea: {e}"
    return render_template('create_task.html')

@app.route('/task/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    tarea = Tarea.query.get_or_404(id)
    if request.method == 'POST':
        tarea.titulo = request.form['titulo']
        tarea.descripcion = request.form['descripcion']
        tarea.fecha_vencimiento = datetime.strptime(request.form['fecha'], '%Y-%m-%d')
        tarea.prioridad = request.form['prioridad']
        tarea.completada = request.form.get('completada') == 'on'
        try:
            db.session.commit()
            flash('Tarea editada exitosamente.', 'success')
            return redirect(url_for('list_tasks'))
        except Exception as e:
            flash('Error al editar la tarea.', 'danger')
            return f"Error al editar la tarea: {e}"
    return render_template('edit_task.html', tarea=tarea)

@app.route('/task/delete/<int:id>')
@login_required
def delete_task(id):
    tarea = Tarea.query.get_or_404(id)
    try:
        db.session.delete(tarea)
        db.session.commit()
        flash('Tarea eliminada exitosamente.', 'success')
    except Exception as e:
        flash('Error al eliminar la tarea.', 'danger')
        return f"Error al eliminar la tarea: {e}"
    return redirect(url_for('list_tasks'))

@app.route('/task/complete/<int:id>', methods=['POST'])
@login_required
def complete_task(id):
    tarea = Tarea.query.get_or_404(id)
    try:
        tarea.completada = not tarea.completada
        db.session.commit()
        if tarea.completada:
            flash('Tarea marcada como completada.', 'success')
        else:
            flash('Tarea marcada como pendiente.', 'info')
    except Exception as e:
        flash('Error al completar la tarea.', 'danger')
        return f"Error al completar la tarea: {e}"
    return redirect(url_for('list_tasks'))

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

@app.route('/status', methods=['GET'])
def status():
    estado = {
        "version": "1.0.0",
        "environment": "production",
        "status": "OK",
        "timestamp": datetime.utcnow().isoformat() + 'Z'
    }
    return jsonify(estado)

if __name__ == '__main__':
    #app.run(debug=True, host='127.0.0.1', port=5001)
    app.run(debug=True, host='0.0.0.0', port=5000)