from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError

app = Flask(__name__)
app.secret_key = "supersecretkey"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///accounting.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    balance = db.Column(db.Float, default=0.0)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    price = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, default=0)

class Operation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200))

@app.before_request
def create_tables():
    db.create_all()
    if Account.query.first() is None:
        db.session.add(Account(balance=0.0))
        db.session.commit()

@app.route("/", methods=["GET", "POST"])
def index():
    try:
        account = Account.query.first()
        products = Product.query.all()
    except SQLAlchemyError as e:
        flash(f"Database error: {e}", "error")
        account = Account(balance=0.0)
        products = []

    if request.method == "POST":
        form_type = request.form.get("form-type")
        try:
            if form_type == "purchase":
                product_name = request.form["purchase-name"]
                price = float(request.form["purchase-price"])
                quantity = int(request.form["purchase-quantity"])
                total = price * quantity

                if account.balance < total:
                    flash("Insufficient funds for this purchase.", "error")
                else:
                    account.balance -= total
                    product = Product.query.filter_by(name=product_name).first()
                    if product:
                        product.quantity += quantity
                        product.price = price
                    else:
                        product = Product(name=product_name, price=price, quantity=quantity)
                        db.session.add(product)
                    db.session.add(Operation(description=f"Purchased {quantity} of {product_name} at {price} each. Total: {total}"))
                    db.session.commit()
                    flash("Purchase successful.", "success")

            elif form_type == "sale":
                product_name = request.form["sale-name"]
                price = float(request.form["sale-price"])
                quantity = int(request.form["sale-quantity"])

                product = Product.query.filter_by(name=product_name).first()
                if not product or product.quantity < quantity:
                    flash("Not enough stock for this sale.", "error")
                else:
                    total = price * quantity
                    account.balance += total
                    product.quantity -= quantity
                    db.session.add(Operation(description=f"Sold {quantity} of {product_name} at {price} each. Total: {total}"))
                    db.session.commit()
                    flash("Sale successful.", "success")

            elif form_type == "balance":
                operation = request.form["balance-type"]
                amount = float(request.form["balance-amount"])
                if operation == "add":
                    account.balance += amount
                    db.session.add(Operation(description=f"Balance increased by {amount}. New balance: {account.balance}"))
                else:
                    account.balance -= amount
                    db.session.add(Operation(description=f"Balance decreased by {amount}. New balance: {account.balance}"))
                db.session.commit()
                flash("Balance updated successfully.", "success")

        except (ValueError, SQLAlchemyError) as e:
            db.session.rollback()
            flash(f"Error: {e}", "error")

        return redirect(url_for("index"))

    return render_template("index.html", balance=account.balance, warehouse=products)

@app.route("/history/")
@app.route("/history/<int:line_from>/<int:line_to>/")
def history(line_from=None, line_to=None):
    try:
        operations = Operation.query.order_by(Operation.id).all()
        if line_from is not None and line_to is not None:
            line_from = max(0, line_from)
            line_to = min(len(operations), line_to)
            operations = operations[line_from:line_to]
    except SQLAlchemyError as e:
        flash(f"Database error: {e}", "error")
        operations = []

    return render_template("history.html", operations=operations)

if __name__ == "__main__":
    app.run(debug=True)