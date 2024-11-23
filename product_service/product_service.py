import pika
import threading
from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager, jwt_required
from flask_sqlalchemy import SQLAlchemy
import json
# Initialize Flask app and extensions
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///products.db'  # SQLite for Product Service DB
app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Change this to a secure secret key
db = SQLAlchemy(app)
jwtmain = JWTManager(app)

# Product Model (Example for SQLite database)
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.String(200), nullable=True)

# Dummy users database for login
users_db = {
    'user1': {
        'password': 'hashed_password_1',  # Replace with hashed password
        'username': 'user1'
    }
}

# Initialize the database (make sure to run this part only once to create the database)
@app.before_first_request
def create_tables():
    db.create_all()

# RabbitMQ setup function
def get_rabbitmq_channel():
    connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))  # Adjust RabbitMQ hostname if needed
    channel = connection.channel()
    return channel


def rpc_product_price():
    connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
    channel = connection.channel()

    # Declare the RPC queue
    channel.queue_declare(queue='rpc_product_price')

    def on_request(ch, method, properties, body):
        request = json.loads(body.decode())
        product_id = request.get('product_id')
        
        # Fetch product price
        product = Product.query.get(product_id)
        if product:
            response = {"price": product.price, "product_id": product_id}
        else:
            response = {"error": f"Product with ID {product_id} not found."}
        
        # Send response back to the client
        ch.basic_publish(
            exchange='',
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(correlation_id=properties.correlation_id),
            body=json.dumps(response)
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue='rpc_product_price', on_message_callback=on_request)
    print("Awaiting RPC requests...")
    channel.start_consuming()

# Create a new product (Protected by JWT)
@app.route('/product', methods=['POST'])
@jwt_required()
def create_product():
    name = request.json.get('name', None)
    price = request.json.get('price', None)
    description = request.json.get('description', None)

    if not name or not price:
        return jsonify({"msg": "Name and price are required"}), 400

    # Create the product and add to database
    new_product = Product(name=name, price=price, description=description)
    db.session.add(new_product)
    db.session.commit()

    # Send message to RabbitMQ
    channel = get_rabbitmq_channel()
    channel.basic_publish(exchange='',
                          routing_key='product_queue',
                          body=f'New product created: {name}, {price}')

    return jsonify({"msg": "Product created successfully"}), 201

# Get all products (Protected by JWT)
@app.route('/products', methods=['GET'])
@jwt_required()
def get_products():
    products = Product.query.all()
    product_list = [{"id": p.id, "name": p.name, "price": p.price, "description": p.description} for p in products]
    return jsonify(product_list), 200

# Get product by ID (Protected by JWT)
@app.route('/product/<int:id>', methods=['GET'])
@jwt_required()
def get_product(id):
    product = Product.query.get(id)
    if not product:
        return jsonify({"msg": "Product not found"}), 404

    return jsonify({
        "id": product.id,
        "name": product.name,
        "price": product.price,
        "description": product.description
    }), 200

# Update product (Protected by JWT)
@app.route('/product/<int:id>', methods=['PUT'])
@jwt_required()
def update_product(id):
    product = Product.query.get(id)
    if not product:
        return jsonify({"msg": "Product not found"}), 404

    # Update product details
    name = request.json.get('name', product.name)
    price = request.json.get('price', product.price)
    description = request.json.get('description', product.description)

    product.name = name
    product.price = price
    product.description = description

    db.session.commit()

    return jsonify({"msg": "Product updated successfully"}), 200

# Delete product (Protected by JWT)
@app.route('/product/<int:id>', methods=['DELETE'])
@jwt_required()
def delete_product(id):
    product = Product.query.get(id)
    if not product:
        return jsonify({"msg": "Product not found"}), 404

    db.session.delete(product)
    db.session.commit()

    return jsonify({"msg": "Product deleted successfully"}), 200

# Error handler for expired or invalid token
@jwtmain.expired_token_loader
def expired_token_callback():
    return jsonify({"msg": "Token has expired"}), 401

@jwtmain.invalid_token_loader
def invalid_token_callback(error):
    return jsonify({"msg": "Invalid token"}), 401

# Handling missing jwtmain
@jwtmain.unauthorized_loader
def unauthorized_callback(error):
    return jsonify({"msg": "Missing or invalid token"}), 401

# Starting Flask app with background RabbitMQ consumer
if __name__ == '__main__':
    # Start the RabbitMQ consumer in a separate thread
    consumer_thread = threading.Thread(target=rpc_product_price, daemon=True)
    consumer_thread.start()
    
    # Run Flask app
    app.run(host='0.0.0.0', port=5002, debug=True)