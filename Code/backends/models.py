from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin
from sqlalchemy.sql import func
from flask_bcrypt import Bcrypt
from datetime import datetime

db = SQLAlchemy()
bcrypt = Bcrypt()

# Association Table for the many-to-many relationship between Users and Roles
class UserRoles(db.Model):
    __tablename__ = 'user_roles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'))
    role_id = db.Column(db.Integer, db.ForeignKey('role.id', ondelete='CASCADE'))


# User Information Model
class User(db.Model, UserMixin):
    __tablename__ = 'user'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    active = db.Column(db.Boolean, default=True)
    lastLoggedIn = db.Column(db.DateTime, default=func.current_timestamp())

    roles = db.relationship('Role', secondary='user_roles', backref=db.backref('users', lazy='dynamic'))
    
    def __init__(self, email, password, active=True, lastLoggedIn=None):
        self.email = email
        self.password = bcrypt.generate_password_hash(password).decode('utf-8')
        self.active = active
        if lastLoggedIn:
            self.lastLoggedIn = lastLoggedIn


# Role Model
class Role(db.Model, RoleMixin):
    __tablename__ = 'role'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255), nullable=True)  # Add a limit for consistency


class ServiceProfessional(db.Model):
    __tablename__ = 'service_professional'
    id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(10), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', ondelete='SET NULL'), nullable=True)
    experience = db.Column(db.Integer, nullable=True)
    document_filename = db.Column(db.String(255), nullable=True)
    date_created = db.Column(db.DateTime, default=func.current_timestamp())
    status = db.Column(db.String(50), default='Pending')

    # Relationships
    service_requests = db.relationship('Bookings', back_populates='professional', lazy='dynamic',cascade="all, delete")
    addresses = db.relationship('Address', backref='service_professional', lazy='dynamic')
    user = db.relationship('User', backref='service_professional', uselist=False)
    


# Customer Model
class Customer(db.Model):
    __tablename__ = 'customer'
    id = db.Column(db.Integer, db.ForeignKey('user.id', ondelete='CASCADE'), primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(10), nullable=False)

    # Relationships
    addresses = db.relationship('Address', backref='customer', lazy='dynamic')
    service_requests = db.relationship('Bookings', backref='customer', lazy='dynamic')
    user = db.relationship('User', backref='customer', uselist=False)
    #carts = db.relationship('Carts', backref='customer', lazy='dynamic')


# Address Model
class Address(db.Model):
    __tablename__ = 'address'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    location = db.Column(db.String(255))
    city = db.Column(db.String(100))
    state = db.Column(db.String(100))
    zip_code = db.Column(db.String(20))

    # This will serve different models for professionals, customers, or service requests
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='CASCADE'), nullable=True)
    service_professional_id = db.Column(db.Integer, db.ForeignKey('service_professional.id'), nullable=True)
    bookings = db.relationship('Bookings', back_populates='address')


# Service Category Model
class ServiceCategory(db.Model): 
    __tablename__ = 'service_category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    image_url = db.Column(db.String(255), nullable=True)

    services = db.relationship('Service', back_populates='category', cascade="all, delete-orphan")

    def __init__(self, name,image_url):
        self.name = name
        self.image_url =image_url



# Service Model
class Service(db.Model):
    __tablename__ = 'service'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('service_category.id'), nullable=False)
    base_price = db.Column(db.Float, nullable=False)
    time_required = db.Column(db.Integer)
    description = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, default=func.current_timestamp())
    image_url = db.Column(db.String(255), nullable=True)
    
    category = db.relationship('ServiceCategory', back_populates='services')

    def __init__(self, name, category_id, base_price, time_required, description, image_url):
        self.name = name
        self.category_id = category_id
        self.base_price = base_price
        self.time_required = time_required
        self.description = description
        self.image_url = image_url


# Discount Model
class Discount(db.Model):
    __tablename__ = 'discount'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    discount_type = db.Column(db.String(10), nullable=False)  # 'flat' or 'percent'
    is_active = db.Column(db.Boolean, default=True)


# Payments Model
class Payments(db.Model):
    __tablename__ = 'payments'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='pending')
    payment_method = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now())
    booking = db.relationship('Bookings', back_populates='payments')

# Remarks Model
class Remarks(db.Model):
    __tablename__ = 'remarks'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('service_professional.id'), nullable=False)
    Bookings_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=True)
    remark = db.Column(db.String(1000), nullable=True)


# Requesting Cart Model
class RequestingCart(db.Model):
    __tablename__ = 'requesting_cart'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)

    customer = db.relationship('Customer', backref='requesting_cart')
    cart_requests = db.relationship('CartRequests', back_populates='requesting_cart', cascade="all, delete-orphan")


# Cart Requests Model
class CartRequests(db.Model):
    __tablename__ = 'cart_requests'
    id = db.Column(db.Integer, primary_key=True)
    requests_cart_id = db.Column(db.Integer, db.ForeignKey('requesting_cart.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)

    service = db.relationship('Service', backref='cart_requests')
    requesting_cart = db.relationship('RequestingCart', back_populates='cart_requests')

    def __init__(self, requests_cart_id, service_id, quantity):
        self.requests_cart_id = requests_cart_id
        self.service_id = service_id
        self.quantity = quantity

class ServiceRequest(db.Model):
    __tablename__ = 'service_request'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id', ondelete='CASCADE'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('service_professional.id', ondelete='SET NULL'), nullable=True)
    address_id = db.Column(db.Integer, db.ForeignKey('address.id', ondelete='CASCADE'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id', ondelete='CASCADE'), nullable=False)
    requested_date = db.Column(db.DateTime, default=func.current_timestamp())
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(50), default='requested')  # Options: requested, assigned, in_progress, completed, cancelled

    # Relationships
    customer = db.relationship('Customer', backref='service_request')
    professional = db.relationship('ServiceProfessional', backref='service_request')
    address = db.relationship('Address', backref='service_request')
    items = db.relationship('ServiceRequestItems', back_populates='service_request', cascade="all, delete-orphan")

class ServiceRequestItems(db.Model):
    __tablename__ = 'service_request_items'
    id = db.Column(db.Integer, primary_key=True)
    service_request_id = db.Column(db.Integer, db.ForeignKey('service_request.id', ondelete='CASCADE'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', ondelete='CASCADE'), nullable=True)
    scheduled_date = db.Column(db.DateTime, nullable=True)
    completed_date = db.Column(db.DateTime, nullable=True)
    quantity = db.Column(db.Integer, nullable=False)

    # Relationships
    service_request = db.relationship('ServiceRequest', back_populates='items')
    service = db.relationship('Service', backref='service_request_items')

class Bookings(db.Model):
    __tablename__ = 'bookings'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    professional_id = db.Column(db.Integer, db.ForeignKey('service_professional.id'), nullable=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id', ondelete='SET NULL'))
    address_id = db.Column(db.Integer, db.ForeignKey('address.id', ondelete='CASCADE'))
    booking_date = db.Column(db.DateTime, default=datetime.now)
    total_amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.String, default='requested')    # requested, working, completed, cancelled

    # Relationships
    professional = db.relationship('ServiceProfessional', back_populates='service_requests')
    service = db.relationship('Service', backref='bookings', lazy=True)
    booking_details = db.relationship('BookingDetails', uselist=False, back_populates='booking', cascade='all, delete-orphan')
    payments = db.relationship('Payments', uselist=False, back_populates='booking')
    address = db.relationship('Address', back_populates='bookings')

# Booking Details Model
class BookingDetails(db.Model):
    __tablename__ = 'booking_details'
    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    date_of_slot_booked = db.Column(db.DateTime, nullable=False)
    date_of_completion = db.Column(db.DateTime, nullable=True)


    booking = db.relationship('Bookings', back_populates='booking_details')