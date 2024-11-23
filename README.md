# Project Structure

## Components

### Nginx

As reverse proxy

### Redis

For caching and Pub/Sub

### RabbitMQ

For RPC between services

### Order Service

Path Prefix: /order-service

#### [GET] /login

Description: To get access token to access resources

#### [GET] /orders

Description: To get all created orders

#### [POST] /orders

Description: To create a new order.
This action will create notification in two way:

1. Realtime notification via Redis Pub/Sub -> WebSocket
2. Non-realtime notification via Redis Stack

#### [POST] /identity

Description: To get username

#### [POST] /notifications

Description: To get notification list (non-realtime)

#### [WS] /notifications

Description: To get connection to realtime notification

### Product Service

Path Prefix: /product-service

#### [GET] /products

Query Parameters:

1. query

Description: To get all products

#### [POST] /product

Description: To create a new product

#### [GET] /product/{id}

Description: To get a product by id

#### [PUT] /product/{id}

Description: To get a product by id

#### [DELETE] /product/{id}

Description: To delete a product by id

### User Service

Path Prefix: /user-service

#### [GET] /users

Description: To get all users

#### [POST] /users

Description: To create a new user
