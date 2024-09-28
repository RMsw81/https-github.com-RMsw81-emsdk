import re
from flask import Flask, jsonify, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import pymysql.cursors
import subprocess
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = '9iKjn_0p@pL'

# Leggi le variabili d'ambiente
db_host = os.getenv('DB_HOST', 'localhost')
db_port = int(os.getenv('DB_PORT', 3306))
db_user = os.getenv('DB_USER', 'user')
db_password = os.getenv('DB_PASSWORD', 'password')
db_name = os.getenv('DB_NAME', 'db')

# Crea la connessione al database
def get_db_connection():
    try:
        return pymysql.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            database=db_name,
            port=db_port,
            cursorclass=pymysql.cursors.DictCursor
        )
    except pymysql.MySQLError as e:
        print(f"Errore nella connessione al database: {e}")
        return None

# Inizializza Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Funzione per creare il database e la tabella
def create_database_and_table():
    connection = pymysql.connect(
        host=db_host,
        user=db_user,
        password=db_password
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("CREATE DATABASE IF NOT EXISTS db")
            connection.select_db('db')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) NOT NULL UNIQUE,
                    password VARCHAR(510) NOT NULL
                )
            ''')
            connection.commit()
    except pymysql.MySQLError as e:
        print(f"Errore nella creazione del database o della tabella: {e}")
    finally:
        connection.close()

# Esegui la creazione del database e della tabella prima di avviare l'app
create_database_and_table()

# UserMixin e User
class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

@login_manager.user_loader
def load_user(user_id):
    connection = get_db_connection()
    try:
        with connection.cursor() as cursor:
            sql = 'SELECT * FROM user WHERE id = %s'
            cursor.execute(sql, (user_id,))
            user = cursor.fetchone()
            if user:
                return User(user['id'], user['username'], user['password'])
    except pymysql.MySQLError as e:
        print(f"Errore nel caricamento dell'utente: {e}")
    finally:
        connection.close()
    return None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_game', methods=['POST'])
@login_required
def start_game():
    try:
        game_script = 'puzzle.py'
        if not os.path.isfile(game_script):
            return jsonify({'error': f'Script {game_script} non trovato'}), 404

        result = subprocess.Popen(['python3', game_script, current_user.username], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = result.communicate()

        if result.returncode != 0:
            return jsonify({'error': stderr.decode('utf-8')}), 500

        return jsonify({'status': 'Gioco avviato'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/start_memory', methods=['POST'])
@login_required
def start_memory():
    try:
        game_script = 'memory.py'
        if not os.path.isfile(game_script):
            return jsonify({'error': f'Script {game_script} non trovato'}), 404

        result = subprocess.Popen(['python3', game_script, current_user.username], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = result.communicate()

        if result.returncode != 0:
            return jsonify({'error': stderr.decode('utf-8')}), 500

        return jsonify({'status': 'Memory game avviato'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def validate_password(password):
    """Verifica se la password soddisfa i criteri richiesti."""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Verifica che tutti i campi siano compilati
        if not username or not password or not confirm_password:
            flash('Tutti i campi sono richiesti', 'danger')
            return redirect(url_for('register'))

        # Verifica che l'username sia una email valida
        if not re.match(r"[^@]+@[^@]+\.[^@]+", username):
            flash('L\'username deve essere un\'email valida.', 'danger')
            return redirect(url_for('register'))

        # Verifica la validità della password
        if not validate_password(password):
            flash('La password deve contenere almeno 8 caratteri, una lettera maiuscola, un numero e un carattere speciale.', 'danger')
            return redirect(url_for('register'))

        # Verifica se la password e la conferma password corrispondono
        if password != confirm_password:
            flash('Le password non corrispondono.', 'danger')
            return redirect(url_for('register'))

        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = 'SELECT * FROM user WHERE username = %s'
                cursor.execute(sql, (username,))
                user = cursor.fetchone()
                
                if user:
                    flash('Username già esistente. Per favore scegli un nome diverso.', 'danger')
                    return redirect(url_for('register'))
                
                hashed_password = generate_password_hash(password)
                sql = 'INSERT INTO user (username, password) VALUES (%s, %s)'
                cursor.execute(sql, (username, hashed_password))
                connection.commit()
                flash('Registrazione avvenuta con successo! Per favore effettua il login.', 'success')
                
                return redirect(url_for('login'))
        except pymysql.MySQLError as e:
            flash(f'Errore durante la registrazione: {e}', 'danger')
            print(f"Errore durante la registrazione: {e}")
        finally:
            connection.close()
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        connection = get_db_connection()
        try:
            with connection.cursor() as cursor:
                sql = 'SELECT * FROM user WHERE username = %s'
                cursor.execute(sql, (username,))
                user = cursor.fetchone()
                
                if user and check_password_hash(user['password'], password):
                    user_obj = User(user['id'], user['username'], user['password'])
                    login_user(user_obj)
                    return redirect(url_for('index'))
                else:
                    flash('Accesso fallito. Controlla username e/o password', 'danger')
        except pymysql.MySQLError as e:
            flash(f'Errore durante il login: {e}', 'danger')
            print(f"Errore nel database durante il login: {e}")
        finally:
            connection.close()
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
