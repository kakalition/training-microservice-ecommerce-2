import json
import threading
import time
import pika
import uuid

client = None

# Order
class RpcClient:
    def __init__(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('rabbitmq'))
        self.channel = self.connection.channel()

        # Declare callback queue
        result = self.channel.queue_declare(queue='rpc_product_price')

        self.callback_queue = result.method.queue
        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self.on_response,
            auto_ack=True
        )

        # self.channel.basic_qos(prefetch_count=1)

        consumer_thread = threading.Thread(target=lambda: self.channel.start_consuming, daemon=True)
        consumer_thread.start()
    
    @staticmethod
    def get_instance():
        global client

        if client == None: 
            client = RpcClient()

        return client

    def on_response(self, ch, method, properties, body):
        # if self.corr_id == properties.correlation_id:
        #     self.response = body
        print(f'ON RESPNSE: {body}')
        self.response = body

    def call(self, product_id):
        self.response = None
        self.corr_id = str(uuid.uuid4())
        self.channel.basic_publish(
            exchange='',
            routing_key='rpc_product_price',
            # properties=pika.BasicProperties(
            #     reply_to=self.callback_queue,
            #     correlation_id=self.corr_id
            # ),
            body=json.dumps({"product_id": product_id})
        )

        while self.response is None:
            self.connection.process_data_events(10)

        print(f"Self Rseponse: {self.response}")

        return json.loads(self.response.decode())
