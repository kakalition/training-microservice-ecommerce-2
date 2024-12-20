from flask import Flask, request, jsonify
import sqlite3

from flask_jwt_extended import JWTManager, jwt_required

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'  # SQLite for Product Service DB
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Change this to a secure secret key
jwtmain = JWTManager(app)

# Initialize SQLite Database
def init_user_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/user-service/users', methods=['POST'])
def create_user():
    data = request.json
    name, email = data['name'], data['email']
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (name, email) VALUES (?, ?)', (name, email))
        conn.commit()
        return jsonify({"message": "User created"}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already exists"}), 400
    finally:
        conn.close()

@app.route('/user-service/users', methods=['GET'])
def list_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM users')
    users = cursor.fetchall()
    conn.close()
    return jsonify([{"id": user[0], "name": user[1], "email": user[2]} for user in users])

if __name__ == '__main__':
    init_user_db()
    app.run(host='0.0.0.0', port=5001)