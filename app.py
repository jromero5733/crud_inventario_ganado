from flask import Flask, request, render_template, redirect, jsonify, send_file, flash, url_for
import mysql.connector
from mysql.connector import Error
from config import Config
import random
import string
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

# Inicialización de la aplicación Flask
app = Flask(__name__)
app.config.from_object(Config)

app.config['SECRET_KEY'] = 'ganado123'

# Función para conectar a la base de datos MySQL
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host=app.config['MYSQL_HOST'],
            user=app.config['MYSQL_USER'],
            password=app.config['MYSQL_PASSWORD'],
            database=app.config['MYSQL_DATABASE']
        )
        return connection
    except Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

# Función para obtener todas las razas
def get_razas():
    conn = get_db_connection()
    if conn is None:
        print("Error: no se pudo conectar a la base de datos.")
        return []

    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM razas")
        razas = cursor.fetchall()
        print(f"Razas obtenidas: {razas}")  # Mensaje de depuración
        return razas
    except Error as e:
        print(f"Error al obtener razas: {e}")
        return []
    finally:
        conn.close()


# Ruta para mostrar la página principal con los registros filtrados
@app.route('/')
def index():
    razas = get_razas()
    conn = get_db_connection()
    if conn is None:
        return "Error al conectar con la base de datos.", 500


    cursor = conn.cursor(dictionary=True)

    # Obtener parámetros de filtro de la URL (search, raza, edad, precio, etc.)
    filter_type = request.args.get('filter_type', 'all')
    search = request.args.get('search', '').strip()
    raza = request.args.get('raza', '').strip()
    min_edad = request.args.get('min_edad', type=int)
    max_edad = request.args.get('max_edad', type=int)
    min_precio = request.args.get('min_precio', type=float)
    max_precio = request.args.get('max_precio', type=float)
    min_peso = request.args.get('min_peso', type=float)
    max_peso = request.args.get('max_peso', type=float)

    # Construcción de la consulta con filtros aplicados
    query = "SELECT ganado.id, ganado.peso, ganado.edad, ganado.precio, razas.nombre AS raza FROM ganado JOIN razas ON ganado.raza_id = razas.id WHERE 1=1"
    params = []

    # Filtrado según los parámetros especificados
    if filter_type == 'search' and search:
        query += " AND ganado.id = %s"
        params.append(search)
    if filter_type == 'raza' and raza:
        query += " AND ganado.raza_id LIKE %s"
        params.append(raza)
    if filter_type == 'age':
        if min_edad is not None:
            query += " AND ganado.edad >= %s"
            params.append(min_edad)
        if max_edad is not None:
            query += " AND ganado.edad <= %s"
            params.append(max_edad)
    if filter_type == 'price':
        if min_precio is not None:
            query += " AND ganado.precio >= %s"
            params.append(min_precio)
        if max_precio is not None:
            query += " AND ganado.precio <= %s"
            params.append(max_precio)
    if filter_type == 'weight':
        if min_peso is not None:
            query += " AND ganado.peso >= %s"
            params.append(min_peso)
        if max_peso is not None:
            query += " AND ganado.peso <= %s"
            params.append(max_peso)


    # Ejecutar la consulta y obtener los resultados
    cursor.execute(query, params)
    ganado = cursor.fetchall()
    conn.close()

    return render_template('index.html', ganado=ganado, razas=razas, filter_type=filter_type, search=search, raza=raza, min_edad=min_edad, max_edad=max_edad, min_precio=min_precio, max_precio=max_precio, min_peso=min_peso, max_peso=max_peso)

# Ruta para mostrar el formulario de agregar ganado
@app.route('/add', methods=['GET', 'POST'])
def add_ganado():
    if request.method == 'POST':
        data = request.form
        id = generate_random_id()
        raza = data['raza']  # ID de la raza seleccionada
        peso = float(data['peso'])
        edad = int(data['edad'])
        precio = float(data['precio'])

        # Verificar si el ganado con el mismo id o alguna otra combinación ya existe
        conn = get_db_connection()
        if conn is None:
            return "Error al conectar con la base de datos.", 500

        cursor = conn.cursor()
        try:
            # Verificar si el ID ya existe en la base de datos
            cursor.execute('SELECT COUNT(*) FROM ganado WHERE id = %s', (id,))
            if cursor.fetchone()[0] > 0:
                flash("El ID del ganado ya existe. Por favor, intente con otro.", "error")
                return render_template('add_ganado.html', razas=get_razas())

            # Verificar si ya existe un ganado con la misma raza, peso, edad y precio
            cursor.execute('''SELECT COUNT(*) FROM ganado WHERE raza_id = %s AND peso = %s AND edad = %s AND precio = %s''', 
                           (raza, peso, edad, precio))
            if cursor.fetchone()[0] > 0:
                flash("Ya existe un ganado con los mismos datos. Por favor, modifique la información.", "error")
                return render_template('add_ganado.html', razas=get_razas())

            # Insertar el ganado si no existe un duplicado
            cursor.execute('''INSERT INTO ganado (id, raza_id, peso, edad, precio) VALUES (%s, %s, %s, %s, %s)''', 
                           (id, raza, peso, edad, precio))
            conn.commit()
            flash("Ganado agregado exitosamente.", "success")

        except Error as e:
            conn.rollback()
            print(f"Error al agregar ganado: {e}")
            return "Error al agregar ganado.", 500
        finally:
            conn.close()

        return redirect('/')

    razas = get_razas()
    return render_template('add_ganado.html', razas=razas)


# Función para generar un ID aleatorio de 6 caracteres para un nuevo registro
def generate_random_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# Ruta para agregar una nueva raza
@app.route("/add_raza", methods=["GET", "POST"])
def add_raza():
    if request.method == "POST":
        raza = request.form["raza"]

        # Verificar si la raza ya existe en la base de datos
        conn = get_db_connection()
        if conn is None:
            return "Error al conectar con la base de datos.", 500

        cursor = conn.cursor()
        try:
            # Verificar si ya existe una raza con el mismo nombre
            cursor.execute("SELECT COUNT(*) FROM razas WHERE nombre = %s", (raza,))
            if cursor.fetchone()[0] > 0:
                flash("La raza ya existe. Por favor, ingrese un nombre diferente.", "error")
                return render_template("add_raza.html")

            # Insertar la nueva raza si no existe un duplicado
            cursor.execute("INSERT INTO razas (nombre) VALUES (%s)", (raza,))
            conn.commit()
            flash("Raza agregada con éxito", "success")
        except Error as e:
            conn.rollback()
            flash(f"Error al agregar raza: {e}", "error")
        finally:
            conn.close()

        return redirect(url_for("add_raza"))

    return render_template("add_raza.html")


# Ruta para actualizar un registro de ganado
@app.route('/update/<string:id>', methods=['GET', 'POST'])
def update_ganado(id):
    razas = get_razas()
    conn = get_db_connection()
    if conn is None:
        return "Error al conectar con la base de datos.", 500
    
    cursor = conn.cursor(dictionary=True)

    if request.method == 'GET':
        cursor.execute('SELECT * FROM ganado WHERE id = %s', (id,))
        ganado = cursor.fetchone()
        conn.close()
        if ganado is None:
            return "Ganado no encontrado.", 404
        return render_template('update_ganado.html', ganado=ganado, razas=razas)

    if request.method == 'POST':
        data = request.form
        raza = data['raza']
        peso = float(data['peso'])
        edad = int(data['edad'])
        precio = float(data['precio'])

        try:
            cursor.execute('''UPDATE ganado SET raza_id=%s, peso=%s, edad=%s, precio=%s WHERE id=%s''', (raza, peso, edad, precio, id))
            conn.commit()
        except Error as e:
            conn.rollback()
            print(f"Error al actualizar ganado: {e}")
            return "Error al actualizar ganado.", 500
        finally:
            conn.close()

        return redirect('/')

# Ruta para eliminar un ganado
@app.route('/delete/<string:id>', methods=['POST'])
def delete_ganado(id):
    conn = get_db_connection()
    if conn is None:
        return "Error al conectar con la base de datos.", 500
    
    try:
        cursor = conn.cursor()
        cursor.execute('DELETE FROM ganado WHERE id=%s', (id,))
        conn.commit()
    except Error as e:
        conn.rollback()
        print(f"Error al eliminar ganado: {e}")
        return "Error al eliminar ganado.", 500
    finally:
        conn.close()

    return redirect('/')

# Función para generar el reporte en formato PDF
def generate_pdf_report(data):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    total_ganado = len(data)
    razas_count = {}
    for item in data:
        raza = item['raza']
        if raza not in razas_count:
            razas_count[raza] = 0
        razas_count[raza] += 1

    c.drawString(100, height - 100, "Reporte de Ganado")
    y_position = height - 130

    c.drawString(100, y_position, f"Total de ganado: {total_ganado}")
    y_position -= 20
    for raza, count in razas_count.items():
        c.drawString(100, y_position, f"Raza {raza}: {count} ganado(s)")
        y_position -= 20

    y_position -= 20  # Añadir espacio antes de los detalles del ganado
    for item in data:
        c.drawString(100, y_position, f"ID: {item['id']} - Raza: {item['raza']} - Peso: {item['peso']}kg - Edad: {item['edad']} - Precio: ${item['precio']}")
        y_position -= 20

    c.showPage()
    c.save()

    buffer.seek(0)
    return buffer


# Ruta para exportar el reporte en formato PDF
@app.route('/report/pdf')
def export_pdf():
    conn = get_db_connection()
    if conn is None:
        return "Error al conectar con la base de datos.", 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT ganado.id, ganado.peso, ganado.edad, ganado.precio, razas.nombre AS raza FROM ganado JOIN razas ON ganado.raza_id = razas.id')
    ganado_data = cursor.fetchall()
    conn.close()

    pdf_data = generate_pdf_report(ganado_data)
    return send_file(pdf_data, as_attachment=True, download_name="reporte_ganado.pdf", mimetype="application/pdf")

# Ruta para exportar el reporte en formato CSV
@app.route('/report/csv')
def export_csv():
    conn = get_db_connection()
    if conn is None:
        return "Error al conectar con la base de datos.", 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT ganado.id, ganado.peso, ganado.edad, ganado.precio, razas.nombre AS raza FROM ganado JOIN razas ON ganado.raza_id = razas.id")
    ganado = cursor.fetchall()
    conn.close()

    total_ganado = len(ganado)
    razas_count = {}
    for item in ganado:
        raza = item['raza']
        if raza not in razas_count:
            razas_count[raza] = 0
        razas_count[raza] += 1

    # Agregar los totales al inicio del CSV
    df = pd.DataFrame(ganado)
    razas_summary = [{"raza": "Total ganado", "count": total_ganado}]
    for raza, count in razas_count.items():
        razas_summary.append({"raza": f"Raza {raza}", "count": count})

    df_summary = pd.DataFrame(razas_summary)
    df_combined = pd.concat([df_summary, df], ignore_index=True)

    csv_report = df_combined.to_csv(index=False)
    return send_file(BytesIO(csv_report.encode()), as_attachment=True, download_name="reporte_ganado.csv", mimetype="text/csv")


# Ruta para exportar el reporte en formato Excel
@app.route('/report/excel')
def export_excel():
    conn = get_db_connection()
    if conn is None:
        return "Error al conectar con la base de datos.", 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT ganado.id, ganado.peso, ganado.edad, ganado.precio, razas.nombre AS raza FROM ganado JOIN razas ON ganado.raza_id = razas.id")
    ganado = cursor.fetchall()
    conn.close()

    total_ganado = len(ganado)
    razas_count = {}
    for item in ganado:
        raza = item['raza']
        if raza not in razas_count:
            razas_count[raza] = 0
        razas_count[raza] += 1

    # Crear el DataFrame para los detalles del ganado
    df = pd.DataFrame(ganado)

    # Crear un DataFrame con el resumen de las razas y total
    razas_summary = [{"raza": "Total ganado", "count": total_ganado}]
    for raza, count in razas_count.items():
        razas_summary.append({"raza": f"Raza {raza}", "count": count})

    df_summary = pd.DataFrame(razas_summary)

    # Escribir ambos DataFrames en un solo archivo Excel
    excel_report = BytesIO()
    with pd.ExcelWriter(excel_report, engine='openpyxl') as writer:
        df_summary.to_excel(writer, index=False, sheet_name="Resumen")
        df.to_excel(writer, index=False, sheet_name="Ganado")
    
    excel_report.seek(0)
    return send_file(excel_report, as_attachment=True, download_name="reporte_ganado.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


if __name__ == '__main__':
    app.run(debug=True)
