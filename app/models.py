
from .extensions import db
from datetime import datetime

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))

class Vehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    license_plate = db.Column(db.String(16), index=True)
    brand = db.Column(db.String(120))
    model = db.Column(db.String(120))
    year = db.Column(db.String(10))

class WorkOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    vehicle_id = db.Column(db.Integer, db.ForeignKey('vehicle.id'))
    notes = db.Column(db.Text)

    customer = db.relationship('Customer', backref='workorders')
    vehicle = db.relationship('Vehicle', backref='workorders')
