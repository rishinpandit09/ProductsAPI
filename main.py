from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import csv

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orders.db'
db = SQLAlchemy(app)


# Define the database models
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)

    def __repr__(self):
        return f'<Product {self.name}>'


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<Order {self.id}>'


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<OrderItem {self.id}>'


# Route for Adding Products
@app.route('/addProduct', methods=['POST'])
def add_product():
    products_data = request.get_json()
    product_items = products_data.get('products_data', [])

    for item in product_items:
        product_name = item['product_name']
        price = item['price']

        product = Product.query.filter_by(name=product_name).first()
        if product:
            product.price = price
        else:
            new_product = Product(name=product_name, price=price)
            db.session.add(new_product)

    db.session.commit()

    return jsonify({'message': 'Products created successfully'})


# Route for creating orders
@app.route('/orders', methods=['POST'])
def create_order():
    order_data = request.get_json()
    order_items = order_data.get('order_items', [])

    order = Order()
    db.session.add(order)
    db.session.commit()

    for item in order_items:
        product_name = item['product_name']
        quantity = item['quantity']

        product = Product.query.filter_by(name=product_name).first()
        if not product:
            return jsonify({'error': f'Product {product_name} not found'})

        order_item = OrderItem(order_id=order.id, product_id=product.id, quantity=quantity)
        db.session.add(order_item)

    db.session.commit()

    return jsonify({'message': 'Order created successfully'})


# Route for uploading product information in CSV format
@app.route('/products/upload', methods=['POST'])
def upload_products():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'})
    file = request.files['file']

    if file.filename == '':
        return jsonify({'error': 'No file selected'})
    with open('products.csv', 'r') as data_file:
        file = csv.reader(data_file)
    if file:
        csv_data = csv.reader(file)
        for row in csv_data:
            product_name = row[0]
            price = float(row[1])

            product = Product.query.filter_by(name=product_name).first()
            if product:
                product.price = price
            else:
                new_product = Product(name=product_name, price=price)
                db.session.add(new_product)

        db.session.commit()

        return jsonify({'message': 'Product information uploaded successfully'})


# Route for viewing the past 3 months' orders report
@app.route('/orders/report', methods=['GET'])
def orders_report():
    today = datetime.now().date()
    three_months_ago = today - timedelta(days=90)
    try:
        report = db.session.query(
            Product.name,
            Product.price,
            db.func.sum(OrderItem.quantity).label('order_quantity'),
            (Product.price * db.func.sum(OrderItem.quantity)).label('total_amount')
        ).join(OrderItem).join(Order).filter(
            Order.order_date >= three_months_ago,
            Order.order_date <= today
        ).group_by(Product.name, Product.price).all()

        report_data = []
        for name, price, order_quantity, total_amount in report:
            report_data.append({
                'Product Name': name,
                'Price': price,
                'Order Quantity': order_quantity,
                'Total Amount': total_amount
            })

        return jsonify({'report': report_data})
    except Exception as e:
        print(e)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        app.run()
