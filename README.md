Configuración de la Aplicación

Pasos necesarios para configurar y ejecutar la aplicación correctamente: 

1. Librerías de Python

Ejecuta los siguientes comandos para instalar las dependencias necesarias:

pip install Flask flask-mysqldb flask-bootstrap

pip install mysql-connector-python

pip install reportlab pandas openpyxl


2. Configuración de la Base de Datos

Utiliza el siguiente comando para configurar una instancia de MySQL utilizando Docker:

docker run -d --name mysql_ganado \
  -e MYSQL_ROOT_PASSWORD=ganado_root_pass \
  -e MYSQL_DATABASE=ganado_db \
  -e MYSQL_USER=ganado_user \
  -e MYSQL_PASSWORD=ganado_pass \
  -p 3306:3306 \
  -v mysql_data:/var/lib/mysql \
  mysql:latest
  
3. Estructura de las tablas para la base de datos:

Tabla razas

CREATE TABLE razas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nombre VARCHAR(255) UNIQUE NOT NULL
);

Tabla ganado

CREATE TABLE ganado (
    id VARCHAR(6) UNIQUE PRIMARY KEY,
    raza_id INT NOT NULL,
    peso DECIMAL(10,2),
    edad INT,
    precio DECIMAL(10,2),
    FOREIGN KEY (raza_id) REFERENCES razas(id)
);
