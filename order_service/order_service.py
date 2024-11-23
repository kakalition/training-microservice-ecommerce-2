from flask import Flask, request, jsonify
import sqlite3
import jwt
from functools import wraps
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from flask_sqlalchemy import SQLAlchemy
import pika
import redis

from flask_sock import Sock

import rpc
import rpc.rpc_client

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'  # SQLite for Product Service DB

sock = Sock(app)
sock.init_app(app)

jwtmain = JWTManager(app)
db = SQLAlchemy(app)

redis_client = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)

# Setup the JWT configuration
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Change this to a secure key in production
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)

# Initialize SQLite Database
def init_order_db():
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Helper function to verify credentials (this is just an example, use DB in real apps)
def verify_credentials(username, password):
    # Dummy check for simplicity. Replace with actual DB validation.
    return username == "admin" and password == "admin"

def send_rabbitmq_message(message):
    connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))  # Sesuaikan hostname RabbitMQ
    channel = connection.channel()

    # Pastikan queue ada
    channel.queue_declare(queue='product_queue')

    # Kirim pesan
    channel.basic_publish(exchange='',
        routing_key='product_queue',
        body=message)
    connection.close()
@app.route('/order-service/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')

    # Validate user credentials
    if verify_credentials(username, password):
        # Create JWT token
        access_token = create_access_token(identity=username)
        return jsonify(access_token=access_token), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 401

# Protect routes with JWT
def jwt_required_custom(fn):
    """ Custom Decorator to Protect Endpoints """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization', None)
        if not auth_header:
            return jsonify({"msg": "Missing Authorization Header"}), 401
        
        # Extract JWT token from Authorization header
        try:
            token = auth_header.split(" ")[1]
            # Decode and verify JWT token
            payload = jwt.decode(token, app.config['JWT_SECRET_KEY'], algorithms=["HS256"])
            user_identity = payload['sub']  # Get user from the payload (sub is the identity)
            # Optionally store user identity in a request global variable for later use
            request.user_identity = user_identity
        except jwt.ExpiredSignatureError:
            return jsonify({"msg": "Token has expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"msg": "Invalid token"}), 401

        return fn(*args, **kwargs)

    return wrapper

@app.route('/order-service/orders', methods=['POST'])
@jwt_required_custom
@jwt_required()
def create_order():
    data = request.json
    user_id, product_id, quantity = data['user_id'], data['product_id'], data['quantity']

    # Request price from product service
    client = rpc.rpc_client.RpcClient.get_instance()
    response = client.call(product_id)

    if "error" in response:
        return jsonify({"error": response["error"]}), 404

    price = response["price"]
    total_price = price * quantity

    redis_client.lpush(get_jwt_identity(), f"Order dengan id produk {product_id} sejumlah {quantity}")
    redis_client.publish("NOTIFICATION", f"Order dengan id produk {product_id} sejumlah {quantity}")

    # Insert order into the database
    conn_order = sqlite3.connect('orders.db')
    cursor_order = conn_order.cursor()
    cursor_order.execute('INSERT INTO orders (user_id, product_id, quantity, total_price) VALUES (?, ?, ?, ?)',
                         (user_id, product_id, quantity, total_price))
    conn_order.commit()
    conn_order.close()

    return jsonify({"message": "Order created", "total_price": total_price}), 201

@app.route('/order-service/orders', methods=['GET'])
@jwt_required_custom
def list_orders():
    conn = sqlite3.connect('orders.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM orders')
    orders = cursor.fetchall()
    conn.close()

    return jsonify([{"id": order[0], "user_id": order[1], "product_id": order[2],
                     "quantity": order[3], "total_price": order[4]} for order in orders])

@app.route('/order-service/identity', methods=['GET'])
@jwt_required_custom
@jwt_required()
def get_identity():
    return get_jwt_identity()

@app.route('/order-service/notifications', methods=['GET'])
@jwt_required_custom
@jwt_required()
def get_notifications():
    username = get_jwt_identity()
    result = redis_client.lpop(username, 100) or []

    print(f"LPOP: {username} - {result}")

    return result

@sock.route('/order-service/echo')
def echo(ws):
    ws.send("PING")
    while True:
        ws.send("PING")

        pubsub = redis_client.pubsub()
        pubsub.subscribe('NOTIFICATION')

        for message in pubsub.listen():
            ws.send(message['data'])

if __name__== '__main__':
    init_order_db()
    app.run(host='0.0.0.0',port=5003)
