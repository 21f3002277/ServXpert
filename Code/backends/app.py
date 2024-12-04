from cProfile import label
from ctypes import addressof
from flask import Flask, jsonify, request, abort, send_from_directory, Response
from config import Config
from models import *
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, unset_jwt_cookies
from werkzeug.utils import secure_filename
from datetime import datetime, date, time
import os
import io
from tools import workers, task, SMS_task
from sqlalchemy import and_, func
from sqlalchemy.exc import SQLAlchemyError
import csv
from flask_caching import Cache

# Initialize the Flask application and extensions
app = Flask(__name__)
app.config.from_object(Config)

# Initialising objects in 'app' context
db.init_app(app)
bcrypt.init_app(app)
jwt = JWTManager(app)
cache = Cache(app)

# configuring Celery
celery = workers.celery
celery.conf.update(
    broker_url=app.config["CELERY_BROKER_URL"],
    result_backend=app.config["CELERY_RESULT_BACKEND"],
)
celery.Task = workers.BackendContextTask


app.app_context().push()

# Set up logging
#logging.basicConfig(level=logging.INFO)

# Function to create role 'admin','customer', 'professional'
def create_role():
    # Check if the role 'admin' exists
    admin_role = Role.query.filter_by(name='admin').first()

    # If it doesn't exist, create it
    if not admin_role:
        admin_role = Role(name='admin', description='Administrator role')
        db.session.add(admin_role)
        db.session.commit()

    # Check if the role 'customer' exists
    customer_role = Role.query.filter_by(name='customer').first()

    # If it doesn't exist, create it
    if not customer_role:
        customer_role = Role(name='customer', description='Customer role')
        db.session.add(customer_role)
        db.session.commit()

    # Check if the role 'professional' exists
    professional_role = Role.query.filter_by(name='professional').first()

    # If it doesn't exist, create it
    if not professional_role:
        professional_role = Role(name='professional', description='Service Professional role')
        db.session.add(professional_role)
        db.session.commit()

# Function to create admin user
def create_admin():
    admin_role = Role.query.filter_by(name='admin').first()
    # Check if an admin user already exists by checking the role of the user
    existing_admin = User.query.join(UserRoles).join(Role).filter(Role.name == 'admin').first()

    if existing_admin:
        return jsonify({"message": "Admin already exists"}), 400

    try:
        # Create new admin user
        admin = User(email="admin@servxpert.com", password="admin123")
        db.session.add(admin)
        db.session.commit()

        # Assign the 'admin' role to the new user
        admin_user_role = UserRoles(user_id=admin.id, role_id=admin_role.id)
        db.session.add(admin_user_role)
        db.session.commit()

        return jsonify({"message": "Admin created successfully"}), 200
    except Exception as e:
        db.session.rollback()  # Ensure rollback on error
        return jsonify({"error": str(e)}), 500

with app.app_context():
    db.create_all()  # Create all database tables
    create_role()
    response = create_admin()
    print(response)  # Log the response for debugging purposes

# Configure CORS to allow requests from your front-end application
CORS(app, supports_credentials=True)
#################################################################################################################################################
from datetime import datetime, timedelta, time
import pytz


def states():
    state_cities = {
    'Andhra Pradesh': ['Visakhapatnam', 'Vijayawada', 'Guntur', 'Nellore', 'Kurnool'],
    'Arunachal Pradesh': ['Itanagar', 'Tawang', 'Pasighat', 'Ziro', 'Bomdila'],
    'Assam': ['Guwahati', 'Dibrugarh', 'Silchar', 'Tezpur', 'Jorhat'],
    'Bihar': ['Patna', 'Gaya', 'Bhagalpur', 'Muzaffarpur', 'Purnia'],
    'Chhattisgarh': ['Raipur', 'Bilaspur', 'Durg', 'Korba', 'Jagdalpur'],
    'Goa': ['Panaji', 'Margao', 'Vasco da Gama', 'Mapusa', 'Ponda'],
    'Gujarat': ['Ahmedabad', 'Surat', 'Vadodara', 'Rajkot', 'Bhavnagar'],
    'Haryana': ['Gurugram', 'Faridabad', 'Panipat', 'Ambala', 'Karnal'],
    'Himachal Pradesh': ['Shimla', 'Dharamshala', 'Manali', 'Solan', 'Mandi'],
    'Jharkhand': ['Ranchi', 'Jamshedpur', 'Dhanbad', 'Bokaro', 'Deoghar'],
    'Karnataka': ['Bengaluru', 'Mysuru', 'Hubli', 'Mangalore', 'Belagavi'],
    'Kerala': ['Thiruvananthapuram', 'Kochi', 'Kozhikode', 'Kollam', 'Thrissur'],
    'Madhya Pradesh': ['Bhopal', 'Indore', 'Gwalior', 'Jabalpur', 'Ujjain'],
    'Maharashtra': ['Mumbai', 'Pune', 'Nagpur', 'Nashik', 'Aurangabad'],
    'Manipur': ['Imphal', 'Thoubal', 'Bishnupur', 'Churachandpur', 'Ukhrul'],
    'Meghalaya': ['Shillong', 'Tura', 'Jowai', 'Nongpoh', 'Baghmara'],
    'Mizoram': ['Aizawl', 'Lunglei', 'Serchhip', 'Champhai', 'Lawngtlai'],
    'Nagaland': ['Kohima', 'Dimapur', 'Mokokchung', 'Wokha', 'Tuensang'],
    'Odisha': ['Bhubaneswar', 'Cuttack', 'Rourkela', 'Puri', 'Berhampur'],
    'Punjab': ['Ludhiana', 'Amritsar', 'Jalandhar', 'Patiala', 'Bathinda'],
    'Rajasthan': ['Jaipur', 'Jodhpur', 'Udaipur', 'Ajmer', 'Bikaner'],
    'Sikkim': ['Gangtok', 'Namchi', 'Gyalshing', 'Mangan', 'Pelling'],
    'Tamil Nadu': ['Chennai', 'Coimbatore', 'Madurai', 'Tiruchirappalli', 'Salem'],
    'Telangana': ['Hyderabad', 'Warangal', 'Nizamabad', 'Khammam', 'Karimnagar'],
    'Tripura': ['Agartala', 'Dharmanagar', 'Kailashahar', 'Udaipur', 'Ambassa'],
    'Uttar Pradesh': ['Lucknow', 'Kanpur', 'Agra', 'Varanasi', 'Meerut'],
    'Uttarakhand': ['Dehradun', 'Haridwar', 'Roorkee', 'Haldwani', 'Nainital'],
    'West Bengal': ['Kolkata', 'Howrah', 'Durgapur', 'Asansol', 'Siliguri'],
    'Andaman and Nicobar Islands': ['Port Blair', 'Car Nicobar', 'Diglipur', 'Mayabunder', 'Rangat'],
    'Chandigarh': ['Chandigarh'],
    'Dadra and Nagar Haveli and Daman and Diu': ['Daman', 'Silvassa', 'Diu'],
    'Lakshadweep': ['Kavaratti', 'Minicoy', 'Agatti', 'Amini', 'Kalpeni'],
    'Delhi': ['New Delhi', 'Dwarka', 'Saket', 'Rohini', 'Karol Bagh'],
    'Puducherry': ['Puducherry', 'Karaikal', 'Mahe', 'Yanam'],
    'Ladakh': ['Leh', 'Kargil'],
    'Jammu and Kashmir': ['Srinagar', 'Jammu', 'Anantnag', 'Baramulla', 'Udhampur']}
    return state_cities

def allowed_file(filename):
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route("/login", methods=["POST"])
def loginPage():
    # Collecting data from request
    data = request.json
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error":"All fields are required"}), 400
    
    # Fetch the user and associated roles
    user = User.query.filter_by(email=email).first()

    # Checking credentials
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error":"Invalid credentials"}), 401
    
    # Retrieve user roles
    roles = [role.name for role in user.roles]
    # Creating access token
    access_token = create_access_token(identity={
        "email":user.email,
        "role": roles,
        "id":user.id
    })

    #updating last logged in time
    user.lastLoggedIn = datetime.now()
    db.session.commit()

    return jsonify({"message":"Login successful", "access_token":access_token}), 200

@app.route("/protected")
@jwt_required()
def protected():
    currentUser = get_jwt_identity()
    user = User.query.filter_by(id=currentUser["id"]).first()
    
    # Check if the user has the 'admin' role
    if "admin" not in currentUser["roles"]:
        return jsonify({"error": "Unauthorized"}), 401

    return f'Hey {user.email} you can access this resource', 200

@app.route("/getuserdata", methods=["GET"])
@jwt_required()
def getuserdata():
    currentUser = get_jwt_identity()
    user = User.query.filter_by(id=currentUser["id"]).first()

    if not user:
        return jsonify({"error":"User not found"}), 404
    
    if user.roles[0].name == "professional":
        professional = db.session.get(ServiceProfessional,currentUser['id'])
        user_data = {
            "id":user.id,
            "email":user.email,
            "role":user.roles[0].name,
            "approval_status": professional.status
        }
    else :
        user_data = {
            "id":user.id,
            "email":user.email,
            "role":user.roles[0].name,
        }
    print(user_data)

    return jsonify({"message": "Found User", "user":user_data}), 200

@app.route('/states', methods=['GET'])
def get_states():
    # Return the list of states
    return jsonify(list(states().keys())), 200

@app.route('/cities', methods=['GET'])
def get_cities():
    state = request.args.get('state')
    
    # Check if the state exists in the states() dictionary
    if state and state in states():
        # Return the list of cities for the selected state
        return jsonify(states()[state])  # No comma here
    else:
        # Return an empty list if the state is invalid or not provided
        return jsonify([]), 404  # Optionally, return a 404 status code for invalid state

@app.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    response = jsonify({"message":"Logout successful"})
    unset_jwt_cookies(response)
    return response, 200

@app.route('/ServiceCategory', methods=['GET'])
def get_service_category():
    # Fetch all service categories from the database
    service_categories = ServiceCategory.query.all()
    
    # Prepare a list of dictionaries to represent the categories
    service_category_list = [
        {
            'id': category.id,
            'name': category.name,
            'image_url': category.image_url
        }
        for category in service_categories
    ]
    
    # Return the data as JSON
    return jsonify(service_category_list)

@app.route('/service/<int:category_id>', methods=['GET'])
def get_service(category_id):
    services = Service.query.filter_by(category_id=category_id).all()

    service_list = [
        {
            "id": service.id,
            "name": service.name
        }
        for service in services
    ]

    return jsonify(service_list)

@app.route('/registerProfessional', methods=['POST'])
def registerProfessional():
    # Extract form data
    firstname = request.form.get('firstname')
    lastname = request.form.get('lastname')
    email = request.form.get('email')
    mobile = request.form.get('mobile')
    password = request.form.get('password')
    confirmpassword = request.form.get('confirmpassword')
    service_id = request.form.get('serviceName')
    experience = request.form.get('experience')
    address = request.form.get('address')
    state = request.form.get('state')
    city = request.form.get('city')
    zip_code = request.form.get('zip')
    agreeToTerms = request.form.get('agreeToTerms')
    
    document = request.files['document']
    if document.filename == '':
        return jsonify({'message': 'No selected document'}), 400

    # Check if the uploaded file is a PDF
    if document and document.filename.endswith('.pdf'):
        filename = secure_filename(document.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        document.save(filepath)
        documents =f'{filepath}'    
    else:
        return jsonify({'message': 'Only PDF files are allowed'}), 400
    
    # Validate input data (basic checks)
    if not (firstname and lastname and email and password and service_id and
            experience and address and city and state and zip_code and agreeToTerms):
        return jsonify({'message': 'All fields are required'}), 400
    
    if password != confirmpassword:
        return jsonify({'Password Not Match'})
    
    if agreeToTerms == 'false':
        print(agreeToTerms)
        return jsonify({'error': 'You must agree to the terms and conditions.'}), 400
    print('4')
    try:
        new_user = User(email=email, password=password, active=True)

        # Add user to the database
        db.session.add(new_user)
        db.session.flush()  # Flush to get the user id before committing

        # Create a Service Professional record
        service_professional = ServiceProfessional(
            id=new_user.id,  
            fullname=f'{firstname} {lastname}',
            phone=mobile,
            service_id=int(service_id),  
            experience=int(experience),  
            document_filename=documents  
        )
        # Assign the 'professional' role to the new user
        professional_user_role = UserRoles(user_id=new_user.id, role_id=int(3))
        db.session.add(professional_user_role)

        # Create the address entry
        address = Address(
            location=address,
            city=city,
            state=state,
            zip_code=zip_code,
            service_professional_id=service_professional.id
        )

        # Add professional and address to the database
        db.session.add(service_professional)
        db.session.add(address)
        db.session.commit()
        task.send_welcome_note_professional.delay(email,firstname)
        SMS_task.send_welcome_sms.delay(firstname, mobile)
        return jsonify({'message': 'Registration successful!'}), 201

    except Exception as e:
        print(e)
        db.session.rollback()
        return jsonify({'error': f'Error during registration: {str(e)}'}), 500

@app.route('/registerCustomer', methods=['POST'])
def register_customer():
    """Handle customer registration"""
    data = request.get_json()

    # Extracting form data
    firstname = data.get('firstname')
    lastname = data.get('lastname')
    email = data.get('email')
    mobile = data.get('mobile')
    password = data.get('password')
    address = data.get('address')
    state = data.get('state')
    city = data.get('city')
    zip_code = data.get('zip')

    # Validate data (simplified, you can add more checks)
    if not firstname or not lastname or not email or not password or not address or not state or not city or not zip_code or not mobile:
        return jsonify({"error": "Missing fields"}), 400

    # Check if the email is already registered
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    # Create User and Customer entry
    new_user = User(email=email, password=password)
    db.session.add(new_user)
    db.session.flush()  # Flush to get the user id

    new_customer = Customer(id=new_user.id, fullname=f"{firstname} {lastname}", phone=mobile)
    db.session.add(new_customer)

    # Assign the 'customer' role to the new user
    customer_user_role = UserRoles(user_id=new_user.id, role_id=int(2))
    db.session.add(customer_user_role)
    db.session.commit()

    # Create Address entry
    new_address = Address(location=address, city=city, state=state, zip_code=zip_code, customer_id=new_customer.id)
    db.session.add(new_address)

    try:
        db.session.commit()  # Commit the changes to the database
        task.send_welcome_note_customer.delay(email,firstname)
        return jsonify({"message": "Customer registered successfully"}), 201
    except Exception as e:
        print(e)
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/services', methods=['GET'])
def get_services():
    try:
        # Fetch all service categories
        service_categories = ServiceCategory.query.all()
        categories_list = []

        for category in service_categories:
            services = []
            category_ratings_total = 0  # Sum of ratings for all services in the category
            category_ratings_count = 0  # Count of all ratings in the category
            category_bookings_count = 0  # Total bookings in the category

            for service in category.services:
                service_ratings = []  # Collect ratings for this service
                service_bookings_count = 0  # Count bookings for this service

                for booking in service.bookings:
                    service_bookings_count += 1  # Increment bookings count for the service

                    # Check if the booking has associated remarks
                    if booking.professional:
                        remarks = Remarks.query.filter_by(
                            professional_id=booking.professional.id,
                            Bookings_id=booking.id
                        ).all()

                        for remark in remarks:
                            if remark.rating:  # Ensure the rating exists
                                service_ratings.append(remark.rating)

                # Calculate the average rating for the service
                services_ratings = sum(service_ratings) / len(service_ratings) if service_ratings else None

                # Update category-level totals
                category_ratings_total += sum(service_ratings) if service_ratings else 0
                category_ratings_count += len(service_ratings)
                category_bookings_count += service_bookings_count

                # Append service details to the list
                services.append({
                    'id': service.id,
                    'name': service.name,
                    'category_id': service.category_id,
                    'base_price': service.base_price,
                    'time_required': service.time_required,
                    'description': service.description,
                    'image_url': service.image_url,
                    'services_ratings': services_ratings,
                    'services_bookings_count': service_bookings_count
                })

            # Calculate the average rating for the category
            categories_ratings = (category_ratings_total / category_ratings_count) if category_ratings_count > 0 else None

            # Append category details to the list
            categories_list.append({
                'id': category.id,
                'name': category.name,
                'image_url': category.image_url,
                'services': services,
                'categories_ratings': categories_ratings,
                'categories_bookings_count': category_bookings_count
            })

        return jsonify(categories_list), 200  # Success response
    except SQLAlchemyError as e:
        print(f"Database error: {str(e)}")  # Log database error
        return jsonify({"error": "Failed to fetch services due to a database issue"}), 500
    except Exception as e:
        print(f"Error fetching services: {str(e)}")  # Log generic error
        return jsonify({"error": "Failed to fetch services"}), 500

@app.route('/add_to_cart/<int:service_id>', methods=['POST'])
@jwt_required()
def add_to_cart(service_id):
    current_user = get_jwt_identity()

    # Ensure the user is authenticated
    if current_user['role'] != ['customer']:
        return jsonify({"error":"Unauthorized"}), 401

    # Fetch the service by ID
    service = db.session.get(Service, service_id)
    if not service:
        return jsonify({'error': 'Service not found'}), 404

    # Checking if the user already has a cart
    user_cart = RequestingCart.query.filter_by(customer_id=current_user["id"]).first()

    if not user_cart:
        user_cart = RequestingCart(customer_id=current_user["id"])
        print(current_user['id'])
        try:
            db.session.add(user_cart)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return {"error": "Failed to add product to cart"}, 500

    cart_item = CartRequests.query.filter_by(requests_cart_id=user_cart.id, service_id=service_id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartRequests(requests_cart_id=user_cart.id, service_id=service_id, quantity=1)
        db.session.add(cart_item)
    try:
       db.session.commit()
       return {"message": "Product added to cart successfully"}, 200
    except Exception as e:
       db.session.rollback()
       return {"error": "Failed to add product to cart"}, 500
    
@app.route('/cart/<int:item_id>/delete', methods=['DELETE'])
@jwt_required()
def delete_cart_item(item_id):
    current_user = get_jwt_identity()

    # Ensure the user is authenticated and authorized
    if current_user['role'] != ['customer']:
        return jsonify({"error": "Unauthorized"}), 401

    # Fetch the cart item
    cart_item = db.session.get(CartRequests, item_id)

    # Check if the item exists and belongs to the current user
    if not cart_item:
        return jsonify({"error": "Item not found"}), 404

    # Delete the cart item
    try:
        db.session.delete(cart_item)
        db.session.commit()
        return jsonify({"message": "Item deleted successfully"}), 200
    except Exception as e:
        print(e)
        db.session.rollback()  # Roll back the transaction on error
        return jsonify({"error": "An error occurred while deleting the item"}), 500

@app.route("/view_cart", methods=["GET"])
@jwt_required()
def view_cart():
    # Get the identity of the current user from the JWT token
    this_user = get_jwt_identity()

    # Ensure the user is authenticated and has the 'customer' role
    if 'customer' not in this_user.get('role', []):
        return jsonify({"error": "Unauthorized"}), 401

    try:
        # Query the cart for the specific customer by their user ID
        user_cart = RequestingCart.query.filter_by(customer_id=this_user["id"]).first()

        # If the cart doesn't exist, return a 404 error
        if not user_cart:
            return jsonify({"error": "Cart not found"}), 404

        # Prepare cart data to be sent back in the response
        cart_data = []
        total_price = 0  # Initialize total price

        for cart_item in user_cart.cart_requests:
            # Ensure the service exists and get its details
            service = cart_item.service
            if service:
                item_total = service.base_price * cart_item.quantity  # Calculate the total for this item
                cart_data.append({
                    "id": cart_item.id,
                    "service_id": cart_item.service_id,
                    "service_name": service.name,
                    "base_price": service.base_price,
                    "image_url": service.image_url,
                    "quantity": cart_item.quantity,
                    "total": item_total  # Total price for this item
                })
                total_price += item_total  # Add this item's total to the cart total
            else:
                # If service is not found, log or handle appropriately
                continue  # Skip this item if no valid service found (or you could log this case)

        # Return the cart data and the total price as a JSON response
        response = {
            "cart_items": cart_data,
            "total_price": total_price  # Include the total price of the cart
        }

        return jsonify(response), 200

    except Exception as e:
        # Catch any unforeseen errors and return a generic error message
        return jsonify({"error": "An error occurred while fetching the cart", "message": str(e)}), 500
    
@app.route("/update_cart/<int:item_id>", methods=["PUT"])
@jwt_required()
def update_carts(item_id):
    print(item_id)
    data = request.get_json()
    action = data.get('action')
    print(action)
    current_user = get_jwt_identity()

    # Ensure the user is authenticated and is a customer
    if current_user['role'] != ['customer']:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Find the cart item by service ID
    cart_item = db.session.get(CartRequests,item_id)
    print(cart_item)
    if not cart_item:
        return jsonify({'error': 'Service details not found in cart'}), 404

    # Update quantity based on action
    if action == 'increase':
        cart_item.quantity += 1
    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
        else:
            return jsonify({'error': 'Quantity cannot be less than 1'}), 400
    else:
        return jsonify({'error': 'Invalid action'}), 400

    # Save the updated quantity
    db.session.commit()

    # Return the updated quantity and confirmation message
    return jsonify({
        'message': 'Cart updated successfully',
        'item_id': item_id,
        'quantity': cart_item.quantity
    })

@app.route('/cart_item/<int:item_id>', methods=["GET"])
@jwt_required()
def Cart_item(item_id):
    this_user = get_jwt_identity()
    print(this_user)
    
    if this_user["role"] != ['customer']:
        return {"error": "You are not supposed to do this!"}, 401

    user_cart = RequestingCart.query.filter_by(customer_id=this_user["id"]).first()
    if not user_cart:
        return {"error": "Cart not found"}, 404

    item = None  # Initialize 'item' to avoid UnboundLocalError
    for cart_item in user_cart.cart_requests:
        if cart_item.service_id == item_id:
            print('yes')
            item = {
                "id": cart_item.id,
                "service_id": cart_item.service_id,
                "service_name": cart_item.service.name,
                "base_price": cart_item.service.base_price,
                "image_url": cart_item.service.image_url,
                "quantity": cart_item.quantity,
                "total": cart_item.service.base_price * cart_item.quantity
            }
            break  # Exit the loop once the item is found

    if not item:
        return {"error": "Item not found in cart"}, 404

    return jsonify(item), 200

@app.route('/get-addresses', methods=["GET"])
@jwt_required()
def get_address():
    this_user = get_jwt_identity()
    if this_user["role"] != ['customer']:
        return {"error": "You are not supposed to do this!"}, 401
    
    addresses = Address.query.filter_by(customer_id=this_user["id"])
    address_data = []

    for address in addresses:
        address_data.append({
            "id": address.id,
            "location": address.location,
            "city": address.city,
            "zip_code": address.zip_code
        })
    print(address_data)
    return jsonify(address_data)

@app.route('/get-slots', methods=["GET"])
def get_consecutive_days():
    IST = pytz.timezone('Asia/Kolkata')
    # Get current date and time
    current_datetime = datetime.now(IST)
    current_date = current_datetime.date()
    current_time = current_datetime.time()

    # Define last slot for Booking
    last_slot = time(19, 0)  # 7:00 PM in 24-hour format
    
    # Store the consecutive days with day number and weekday names (3-character format)
    consecutive_days = {}

    # Interval of 30 minutes
    time_interval = timedelta(minutes=30)

    # Define the end time for booking (7:00 PM) for any day
    end_time = time(19, 0)

    def round_to_nearest_half_hour(current_datetime):
        """Rounds the time to the nearest :00 or :30."""
        if current_datetime.minute < 30:
            return current_datetime.replace(minute=30, second=0, microsecond=0)
        else:
            next_hour = current_datetime.hour + 1
            return current_datetime.replace(hour=next_hour, minute=0, second=0, microsecond=0)

    if current_time > time(17, 0):
        # If current time is past 5:00 PM, start from the next day at 8:00 AM
        for i in range(3):
            day = current_date + timedelta(days=i + 1)
            # Convert the day to a string in 'YYYY-MM-DD' format
            day_str = day.strftime('%Y-%m-%d')
            consecutive_days[day_str] = []

            start_time = IST.localize(datetime.combine(day, time(8, 0)))  # Start at 8:00 AM
            end_time_for_day = IST.localize(datetime.combine(day, end_time))  # End at 7:00 PM
            
            # Fill the slots for the day
            current_time = start_time
            while current_time <= end_time_for_day:
                consecutive_days[day_str].append(current_time.strftime('%I:%M %p'))
                current_time += time_interval

    else:
        # If current time is before 5:00 PM, include today's slots from the current time
        for i in range(3):
            day = current_date + timedelta(days=i)
            # Convert the day to a string in 'YYYY-MM-DD' format
            day_str = day.strftime('%Y-%m-%d')
            consecutive_days[day_str] = []

            if i == 0:
                # For today, round the current time to nearest :00 or :30
                start_time = round_to_nearest_half_hour(current_datetime)
            else:
                # For future days, start at 8:00 AM
                start_time = IST.localize(datetime.combine(day, time(8, 0)))

            end_time_for_day = IST.localize(datetime.combine(day, end_time))  # End at 7:00 PM

            # Fill the slots for the day
            current_time = start_time
            while current_time <= end_time_for_day:
                consecutive_days[day_str].append(current_time.strftime('%I:%M %p'))
                current_time += time_interval

    return jsonify(consecutive_days)

@app.route('/apply-coupon', methods=['POST'])
@jwt_required()
def apply_coupon():
    try:
        data = request.json
        coupon_code = data.get('couponCode')

        current_user = get_jwt_identity()
        if current_user["role"] != ['customer']:
            return {"error": "You are not supposed to do this!"}, 401

        if not coupon_code:
            return jsonify({"success": False, "message": "Coupon code is required"}), 400

        # Fetch coupon details
        coupon = Discount.query.filter_by(code=coupon_code, is_active=True).first()
        print(coupon)
        if not coupon:
            return jsonify({"success": False, "message": "Invalid or expired coupon code"}), 404

        # Calculate discount
        if coupon.discount_type == 'flat':
            discount_amount = coupon.amount
        elif coupon.discount_type == 'percent':
            total_amount = data.get('totalAmount', 0)  # Ensure the total amount is passed in request
            discount_amount = (coupon.amount / 100) * total_amount
        else:
            return jsonify({"success": False, "message": "Unknown discount type"}), 500

        return jsonify({
            "success": True,
            "message": "Coupon applied successfully",
            "discount": discount_amount
        }), 200

    except Exception as e:
        print(e)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/professional/today-services', methods=['GET'])
@jwt_required()
def get_today_services():
    # Get the current professional's user ID from the JWT
    current_user = get_jwt_identity()
    if current_user["role"] != ['professional']:
        return {"error": "You are not supposed to do this!"}, 401

    professional = db.session.get(ServiceProfessional,current_user['id'])

    today = datetime.now().date()

    # Query for today's services assigned to the logged-in professional
    query = (
        db.session.query(
            ServiceRequest.id,
            Customer.fullname.label('name'),
            Customer.phone.label('mobileNo'),
            Service.name.label('serviceName'),
            ServiceRequestItems.quantity,
            ServiceRequestItems.scheduled_date.label('slotBooked'),
            ServiceRequest.total_amount.label('pay'),
            ServiceRequest.status.label('status'),
            Address.location.label('location')
            ).distinct()
            .join(Customer, ServiceRequest.customer_id == Customer.id)
            .join(ServiceRequestItems, ServiceRequest.id == ServiceRequestItems.service_request_id)
            .join(Service, ServiceRequestItems.service_id == Service.id)
            .join(Address, ServiceRequest.address_id == Address.id)
            .filter(ServiceRequest.professional_id == current_user['id'],
                    Address.zip_code == professional.addresses[0].zip_code, 
                    func.date(ServiceRequestItems.scheduled_date) == today,
                    Service.id== professional.service_id)
                    
    )

    # Execute the query and fetch results
    today_services = query.all()

    # Convert query results into a list of dictionaries for JSON response
    result = [
        {
            'id': service.id,
            'name': service.name,
            'mobileNo': service.mobileNo,
            'serviceName': service.serviceName,
            'quantity': service.quantity,
            'pay': service.pay,
            'slotBooked': service.slotBooked.strftime('%Y-%m-%d %H:%M:%S') if service.slotBooked else None,
            'status': service.status,
            'location': service.location,
        }
        for service in today_services
    ]

    return jsonify(result)

# Route to get closed services for a professional
@app.route('/api/professional/closed-services', methods=['GET'])
@jwt_required()
def get_closed_services():
    current_user = get_jwt_identity()
    if current_user["role"] != ['professional']:
        return {"error": "You are not supposed to do this!"}, 401

    try:
        # Query closed bookings for the current professional where status is 'completed'
        closed_services = (Bookings.query
                           .filter_by(professional_id=current_user["id"], status='completed')
                           .join(BookingDetails, Bookings.id == BookingDetails.booking_id)
                           .all())

        result = []
        for service in closed_services:
            # Fetch the associated customer
            customer = Customer.query.get(service.customer_id)
            if not customer:
                continue  # Skip if no customer is found

            # Fetch customer's address, if available
            address = Address.query.filter_by(customer_id=customer.id).first()

            # Fetch remarks related to the booking and professional
            remark = Remarks.query.filter_by(
                professional_id=current_user["id"], 
                Bookings_id=service.id
            ).first()

            result.append({
                'id': service.id,
                'customer': {
                    'fullname': customer.fullname,
                    'phone': customer.phone  # Ensure phone exists in the Customer model
                },
                'address': {
                    'location': address.location if address else "N/A"
                },
                'date_of_completion': service.booking_details.date_of_completion.strftime('%Y-%m-%d %H:%M:%S')
                if service.booking_details.date_of_completion else "N/A",
                'rating': remark.rating if remark else "0"
            })

        return jsonify(result), 200

    except Exception as e:
        print(e)
        return {"error": f"An error occurred: {str(e)}"}, 500

# Route to accept a service request
@app.route('/api/bookings/<int:booking_id>/accept', methods=['POST'])
@jwt_required()
def accept_service(booking_id):

    current_user = get_jwt_identity()
    if current_user["role"] != ['professional']:
        return {"error": "You are not supposed to do this!"}, 401
    
    # Find the booking by ID
    booking = Bookings.query.get_or_404(booking_id)
    
    if booking.status != 'Pending':
        abort(400, description='This booking is already accepted or closed.')

    # Mark the booking as 'Accepted'
    booking.status = 'Accepted'
    db.session.commit()

    return jsonify({'message': f'Booking {booking_id} has been accepted.'})

@app.route('/customer/bookings', methods=['GET'])
@jwt_required()
def get_bookings():
    current_user = get_jwt_identity()
    if current_user["role"] != ['customer']:
        return {"error": "You are not supposed to do this!"}, 401

    try:
        # Fetch all bookings for the logged-in customer
        bookings = Bookings.query.filter_by(customer_id=current_user["id"]).all()

        if not bookings:
            return jsonify([]), 200

        # Prepare the response data
        booking_history = []
        for booking in bookings:
            booking_data = {
                'id': booking.id,
                'professional': {
                    'name': booking.professional.fullname if booking.professional else 'N/A'
                },
                'status': booking.status,
                'service': {
                    'name': booking.service.name,
                    'image_url': booking.service.image_url
                },
                'booking_details': {
                    'date_of_slot_booked': booking.booking_details.date_of_slot_booked if booking.booking_details else 'N/A',
                    'date_of_completion': booking.booking_details.date_of_completion if booking.booking_details else 'N/A'
                },
                'payments': {
                    'amount': booking.payments.amount if booking.payments else 'N/A',
                    'status': booking.payments.status if booking.payments else 'N/A',
                    'payment_method': booking.payments.payment_method if booking.payments else 'N/A',
                    'timestamp': booking.payments.timestamp if booking.payments else 'N/A'
                }
            }
            booking_history.append(booking_data)
        #print(booking_history)

        return jsonify(booking_history), 200

    except Exception as e:
        print(e)
        return jsonify({'message': 'Error fetching bookings'}), 500

@app.route('/professional/bookings', methods=['GET'])
@jwt_required()
def get_professional_bookings():

    current_user = get_jwt_identity()
    if current_user["role"] != ['professional']:
        return {"error": "You are not authorized to access this!"}, 401

    try:
        # Fetch all bookings assigned to the logged-in professional
        bookings = Bookings.query.filter_by(professional_id=current_user["id"]).all()

        if not bookings:
            return jsonify([]), 200

        # Prepare the response data
        booking_history = []
        for booking in bookings:
            booking_data = {
                'id': booking.id,
                'customer': {
                    'name': booking.customer.fullname,
                    'contact_info': booking.customer.phone  # Assuming the customer has a contact_info field
                },
                'status': booking.status,
                'service': {
                    'name': booking.service.name,
                    'image_url': booking.service.image_url
                },
                'booking_details': {
                    'date_of_slot_booked': booking.booking_details.date_of_slot_booked,
                    'date_of_completion': booking.booking_details.date_of_completion
                },
                'payments': {
                    'amount': booking.payments.amount,
                    'status': booking.payments.status,
                    'payment_method': booking.payments.payment_method,
                    'timestamp': booking.payments.timestamp
                }
            }
            booking_history.append(booking_data)

        return jsonify(booking_history), 200

    except Exception as e:
        print(e)
        return jsonify({'message': 'Error fetching bookings'}), 500

##################################################################################################################################################################



##################################################################################################################################################################
@app.route('/api/admin/stats', methods=['GET'])
@jwt_required()
def consolidated_stats():

    current_user = get_jwt_identity()
    if current_user["role"] != ['admin']:
        return {"error": "You are not authorized to access this!"}, 401
    
    
    # Query for monthly revenue from Bookings
    revenue_by_month = [
        {
            "raw_timestamp": month,  # raw date object
            "month": datetime.strptime(month, '%Y-%m').strftime('%b %Y'),  # SQLite returns strings for strftime
            "total_revenue": float(revenue),  # convert Decimal to float
        }
        for month, revenue in db.session.query(
            func.strftime('%Y-%m', Payments.timestamp).label('month'),  # Use strftime for year-month
            func.sum(Payments.amount)
        )
        .join(Bookings, Bookings.id == Payments.booking_id)
        .group_by(func.strftime('%Y-%m', Payments.timestamp))  # Group by year-month
        .order_by(func.strftime('%Y-%m', Payments.timestamp))  # Order by year-month
        .all()
    ]

    # Query for most active customers by the number of bookings
    customers_results = (
        db.session.query(
            Customer.fullname.label('customer_name'),
            func.count(Bookings.id).label('bookings_count')
        )
        .join(Bookings, Customer.id == Bookings.customer_id)
        .group_by(Customer.id)
        .order_by(func.count(Bookings.id).desc())
        .limit(5)  # Limit to top 5 customers
        .all()
    )
    customers_data = [{'customer_name': customer_name, 'bookings_count': bookings_count} for customer_name, bookings_count in customers_results]

    # Query for top-rated professionals based on rating in Remarks model
    professionals_results = (
        db.session.query(
            ServiceProfessional.fullname.label('professional_name'),
            func.avg(Remarks.rating).label('average_rating')
        )
        .join(Remarks, ServiceProfessional.id == Remarks.professional_id)
        .filter(Remarks.rating.isnot(None))  # Exclude null ratings
        .group_by(ServiceProfessional.id)
        .order_by(func.avg(Remarks.rating).desc())
        .limit(5)  # Top 5 professionals by average rating
        .all()
    )
    professionals_data = [{'professional_name': professional_name, 'average_rating': round(average_rating, 2)} for professional_name, average_rating in professionals_results]

    # Query for active professionals grouped by service category
    categories_results = (
        db.session.query(
            Service.name.label('category'),
            func.count(ServiceProfessional.id).label('count')
        )
        .join(Service, Service.id == ServiceProfessional.service_id)
        .filter(ServiceProfessional.status == 'Approved')  # Assuming 'status' indicates active/inactive
        .group_by(Service.name)
        .all()
    )
    categories_data = [{'category': category, 'count': count} for category, count in categories_results]

    # Return all data as a consolidated response
    return jsonify({
        "revenue": revenue_by_month,
        "most_active_customers": customers_data,
        "top_rated_professionals": professionals_data,
        "active_professionals_by_category": categories_data
    })

@app.route('/api/professional/stats', methods=['GET'])
@jwt_required()
def get_professional_stats():
    current_user = get_jwt_identity()
    if current_user["role"] != ['professional']:
        return {"error": "You are not authorized to access this!"}, 401

    # Bookings grouped by status for the specific professional
    bookings_by_status = [
        {"status": status, "count": count}
        for status, count in db.session.query(Bookings.status, func.count(Bookings.id))
        .filter(Bookings.professional_id == current_user['id'])
        .group_by(Bookings.status)
        .all()
    ]

    # Revenue by month for the specific professional
    revenue_by_month = [
        {
            "raw_timestamp": month,  # raw date object
            "month": datetime.strptime(month, '%Y-%m').strftime('%b %Y'),  # SQLite returns strings for strftime
            "revenue": float(revenue),  # convert Decimal to float
        }
        for month, revenue in db.session.query(
            func.strftime('%Y-%m', Payments.timestamp).label('month'),  # Use strftime for year-month
            func.sum(Payments.amount)
        )
        .join(Bookings, Bookings.id == Payments.booking_id)
        .filter(Bookings.professional_id == current_user['id'], Payments.status == 'completed')
        .group_by(func.strftime('%Y-%m', Payments.timestamp))  # Group by year-month
        .order_by(func.strftime('%Y-%m', Payments.timestamp))  # Order by year-month
        .all()
    ]
    print(revenue_by_month)

    return jsonify({
        "bookings_by_status": bookings_by_status,
        "revenue_by_month": revenue_by_month,
    })

@app.route('/api/customer/stats', methods=['GET'])
@jwt_required()
def get_customer_stats():
    current_user = get_jwt_identity()
    if current_user["role"] != ['customer']:
        return {"error": "You are not authorized to access this!"}, 401

    # Bookings by Status
    bookings_by_status = (
        db.session.query(Bookings.status, db.func.count(Bookings.id).label("count"))
        .filter(Bookings.customer_id == current_user['id'])
        .group_by(Bookings.status)
        .all()
    )
    bookings_by_status_data = [{"status": status, "count": count} for status, count in bookings_by_status]

    # Average Ratings by Professionals
    ratings_by_professional = (
        db.session.query(
            ServiceProfessional.fullname,
            db.func.avg(Remarks.rating).label("average_rating")
        )
        .join(Remarks, Remarks.professional_id == ServiceProfessional.id)
        .join(Bookings, Bookings.id == Remarks.Bookings_id)
        .filter(Bookings.customer_id == current_user['id'])
        .group_by(ServiceProfessional.fullname)
        .all()
    )
    ratings_by_professional_data = [{"professional": fullname, "average_rating": avg_rating} 
                                    for fullname, avg_rating in ratings_by_professional]

    # Spending by Month
    spending_by_month_data = [
        {
            "raw_timestamp": month,
            "month": datetime.strptime(month, '%Y-%m').strftime('%b %Y'),
            "spending": float(amount),
        }
        for month, amount in db.session.query(
            db.func.strftime('%Y-%m', Bookings.booking_date).label("month"),
            db.func.sum(Bookings.total_amount).label("amount")
        )
        .filter(Bookings.customer_id == current_user['id'])
        .group_by(db.func.strftime('%Y-%m', Bookings.booking_date))
        .order_by(db.func.strftime('%Y-%m', Bookings.booking_date))
        .all()
    ]

    print(spending_by_month_data)

    frequency_by_service = (
        db.session.query(
            Service.name.label("service"),
            func.count(Bookings.id).label("count")
        )
        .join(Bookings, Bookings.service_id == Service.id)
        .filter(Bookings.customer_id == current_user['id'])
        .group_by(Service.name) 
        .all() 
    )
    
    
    frequency_by_service_data = [
        {"service": service, "count": count} for service, count in frequency_by_service
    ]

    print(frequency_by_service_data)

    return jsonify({
        "bookings_by_status": bookings_by_status_data,
        "ratings_by_professional": ratings_by_professional_data,
        "spending_by_month": spending_by_month_data,
        "frequency_by_service": frequency_by_service_data,
    })

##################################################################################################################################################################



##################################################################################################################################################################

@app.route('/api/customer/avaliable/services', methods=['GET'])
@jwt_required()
def get_avaliable_services_by_pincode():

    current_user = get_jwt_identity()
    if current_user["role"] != ['customer']:
        return {"error": "You are not authorized to access this!"}, 401
    
    address = Address.query.filter_by(customer_id = current_user['id']).first()
    print(address.zip_code)

    try:
        service_ids = ( db.session.query(Service.id).distinct()
            .join(ServiceProfessional, ServiceProfessional.service_id == Service.id)
            .join(Address, Address.service_professional_id == ServiceProfessional.id)
            .filter(Address.zip_code == address.zip_code)
            .all()
        )
        
        service_id_list = [service_id[0] for service_id in service_ids]
        print(service_id_list)

        return jsonify({"service_ids": service_id_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

##################################################################################################################################################################



##################################################################################################################################################################

@app.route('/uploads/<path:filename>')
def download_file(filename):
    folder,filename = filename.split('/')

    try:
        return send_from_directory(folder, filename, as_attachment=False)
    except FileNotFoundError:
        abort(404)

@app.route('/api/admin/<int:id>/approveProfessional', methods=['PUT'])
@jwt_required()
def approve_professional(id):
    current_user = get_jwt_identity()
    if current_user["role"] != ['admin']:
        return {"error": "You are not authorized to access this!"}, 401
    try:
        professional = ServiceProfessional.query.get(id)
        if not professional:
            return jsonify({"error": "Professional not found"}), 404

        professional.status = 'Approved'
        db.session.commit()
        return jsonify({"message": "Professional approved successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/<int:id>/rejectProfessional', methods=['PUT'])
@jwt_required()
def reject_professional(id):
    current_user = get_jwt_identity()
    if current_user["role"] != ['admin']:
        return {"error": "You are not authorized to access this!"}, 401
    
    try:
        professional = ServiceProfessional.query.get(id)
        if not professional:
            return jsonify({"error": "Professional not found"}), 404

        professional.status = 'Rejected'
        db.session.commit()
        return jsonify({"message": "Professional rejected successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/<int:id>/flagProfessional', methods=['PUT'])
@jwt_required()
def flag_professional(id):

    current_user = get_jwt_identity()

    # Check user role
    if current_user["role"] != ["admin"]:
        return {"error": "You are not authorized to perform this action."}, 401
    
    try:
        professional = db.session.query(User).join(ServiceProfessional, ServiceProfessional.id == User.id).filter_by(id=id).first()
        print(professional)
        if not professional:
            return jsonify({"error": "Professional not found."}), 404
        print(professional.active)
        professional.active = False  # Assuming False means 'flagged'
        db.session.commit()
        return jsonify({"message": "Professional flagged successfully."}), 200
    except Exception as e:
        print(e)
        return jsonify({"error": "Failed to flag professional."}), 500

@app.route('/api/admin/<int:id>/unflagProfessional', methods=['PUT'])
@jwt_required()
def unflag_professional(id):
    current_user = get_jwt_identity()
    if current_user["role"] != ['admin']:
        return {"error": "You are not authorized to access this!"}, 401
    
    try:
        professional = db.session.query(User).join(ServiceProfessional, ServiceProfessional.id == User.id).filter_by(id=id).first()
        print(professional)
        if not professional:
            return jsonify({"error": "Professional not found."}), 404
        print(professional.active)
        professional.active = True  # Assuming False means 'flagged'
        db.session.commit()
        return jsonify({"message": "Professional flagged successfully."}), 200
    except Exception as e:
        print(e)
        return jsonify({"error": "Failed to flag professional."}), 500

@app.route('/api/admin/<int:id>/flagCustomer', methods=['PUT'])
@jwt_required()
def flag_customer(id):
    current_user = get_jwt_identity()
    if current_user["role"] != ['admin']:
        return {"error": "You are not authorized to access this!"}, 401
    try:
        customer = db.session.query(User).join(Customer, Customer.id == User.id).filter_by(id=id).first()
        if not customer:
            return jsonify({"error": "Customer not found."}), 404
        customer.active = False  # Assuming False means 'flagged'
        db.session.commit()
        return jsonify({"message": "Customer flagged successfully."}), 200
    except Exception as e:
        print(e)
        return jsonify({"error": "Failed to flag customer."}), 500

@app.route('/api/admin/<int:id>/unflagCustomer', methods=['PUT'])
@jwt_required()
def unflag_customer(id):
    current_user = get_jwt_identity()
    if current_user["role"] != ['admin']:
        return {"error": "You are not authorized to access this!"}, 401
    try:
        customer = db.session.query(User).join(Customer, Customer.id == User.id).filter_by(id=id).first()
        if not customer:
            return jsonify({"error": "Customer not found."}), 404
        customer.active = True  # Assuming False means 'flagged'
        db.session.commit()
        return jsonify({"message": "Customer unflagged successfully."}), 200
    except Exception as e:
        print(e)
        return jsonify({"error": "Failed to unflag customer."}), 500

@app.route('/api/admin/<int:id>/deleteCustomer', methods=['DELETE'])
@jwt_required()
def delete_customer(id):
    current_user = get_jwt_identity()
    if current_user["role"] != ['admin']:
        return {"error": "You are not authorized to access this!"}, 401

    try:
        # Fetch the user, customer, and associated addresses
        user = db.session.get(User, id)
        customer = db.session.get(Customer, id)
        addresses = db.session.query(Address).filter(Address.customer_id == id).all()

        # Check if user exists
        if not user:
            return jsonify({"error": "Customer not found."}), 404

        # Delete related records in an order to avoid foreign key issues
        db.session.query(Remarks).filter_by(customer_id=id).delete(synchronize_session=False)
        bookings = db.session.query(Bookings).filter_by(customer_id=id).all()
        for booking in bookings:
            if booking.payments:
                db.session.delete(booking.payments)
            if booking.booking_details:
                db.session.delete(booking.booking_details)
            db.session.delete(booking)

        requests = db.session.query(ServiceRequest).filter_by(customer_id=id).all()
        for request in requests:
            if request.items:
                for item in request.items:
                    db.session.delete(item)
            db.session.delete(request)

        Cart = db.session.query(RequestingCart).filter_by(customer_id=id).first()
        if Cart.cart_requests:
            for service in Cart.cart_requests:
                db.session.delete(service)
        db.session.delete(Cart)

        # Delete addresses explicitly if cascade is not set up
        for address in addresses:
            db.session.delete(address)

        # Delete customer and user records
        db.session.delete(customer)
        db.session.delete(user)

        # Commit all deletions to the database
        db.session.commit()
        return jsonify({"message": "Customer deleted successfully."}), 200

    except Exception as e:
        db.session.rollback()  # Roll back the session in case of error
        print(f"Error deleting customer: {e}")
        return jsonify({"error": "Failed to delete customer."}), 500

@app.route('/api/admin/statsDash', methods=['GET'])
def get_stats():
    # Fetching statistics for the dashboard
    total_customers = Customer.query.count()
    total_professionals = ServiceProfessional.query.count()
    total_services = Service.query.count()

    return jsonify({
        'totalCustomers': total_customers,
        'totalProfessionals': total_professionals,
        'totalServices': total_services
    })

@app.route('/api/admin/recent-users', methods=['GET'])
def get_recent_users():
    try:
        # Fetching recent users excluding those with the 'admin' role
        recent_users = db.session.query(User).join(User.roles).filter(Role.name != 'admin').order_by(User.lastLoggedIn.desc()).limit(5).all()

        users_data = []
        for user in recent_users:
            users_data.append({
                'id': user.id,
                'name': user.email,  # Modify as per your needs, maybe `fullname` instead of `email`
                'email': user.email,
                'role': ', '.join([role.name for role in user.roles]),
                'joined': user.lastLoggedIn
            })

        return jsonify(users_data)
    
    except Exception as e:
        # In case of an error, return a meaningful error message
        return jsonify({"error": str(e)}), 500

@app.route('/service-history', methods=['GET'])
@jwt_required()
def get_service_history():
    current_user = get_jwt_identity()
    if current_user["role"] != ["customer"]:
        return {"error": "You are not supposed to do this!"}, 401

    # Query the database for the customer's booking history
    bookings = Bookings.query.filter_by(customer_id=current_user['id']).all()

    service_history = []
    for booking in bookings:
        # Find the remark associated with this booking
        remark = Remarks.query.filter_by(Bookings_id=booking.id).first()
        
        service_history.append({
            'id': booking.id,
            'service_status': booking.status,
            'slotbooked': booking.booking_details.date_of_slot_booked,
            'service': {
                'name': booking.service.name,
                'description': booking.service.description,
            },
            'professional': {
                'id':  getattr(booking.professional, 'id', 'N/A'),
                'fullname': getattr(booking.professional, 'fullname', 'N/A'),
                'phone': getattr(booking.professional, 'phone', 'N/A')
            },
            'remark': {
                'rating': remark.rating if remark else None,
                'remark_text': remark.remark if remark else None
            }
        })

    return jsonify(service_history)

@app.route('/api/admin/<int:id>/deleteProfessional',methods=['DELETE'])
@jwt_required()
def delete_professional(id):
    current_user = get_jwt_identity()
    if current_user["role"] != ['admin']:
        return {"error": "You are not authorized to access this!"}, 401
    
    try:
      # Fetch the user, customer, and associated addresses
      user = db.session.get(User, id)
      professional = db.session.get(ServiceProfessional, id)
      addresses = db.session.query(Address).filter(Address.service_professional_id == id).all()

      # Check if user exists
      if not user:
        return jsonify({"error": "Professional not found."}), 404
      db.session.query(Remarks).filter_by(professional_id=id).delete(synchronize_session=False)
      requests = db.session.query(ServiceRequest).filter_by(professional_id=id).all()
      for request in requests:
        for item in request.items:
           db.session.delete(item)
        db.session.delete(request)

      bookings = db.session.query(Bookings).filter_by(professional_id=id).all()
      for booking in bookings:
        if booking.payments:
            db.session.delete(booking.payments)
        if booking.booking_details:
            db.session.delete(booking.booking_details)
        db.session.delete(booking)

      # Delete addresses explicitly if cascade is not set up
      for address in addresses:
        db.session.delete(address)

      # Delete customer and user records
      db.session.delete(professional)
      db.session.delete(user)

      # Commit all deletions to the database
      db.session.commit()
      return jsonify({"message": "Professional deleted successfully."}), 200

    except Exception as e:
      db.session.rollback()  # Roll back the session in case of error
      print(f"Error deleting Professional: {e}")
      return jsonify({"error": "Failed to delete Professional."}), 500
    except SQLAlchemyError as e:
        print(e)
        db.session.rollback()
        return jsonify({'error': f'Database error occurred: {str(e)}'}), 500

##########################################################################################################################################################



##########################################################################################################################################################

@app.route('/api/admin/addcategories', methods=['POST'])
@jwt_required()
def add_category():
    data = request.json

    current_user = get_jwt_identity()

    # Check user role
    if current_user["role"] != ["admin"]:
        return {"error": "You are not authorized to perform this action."}, 401

    try:
        new_category = ServiceCategory(name=data['name'],image_url=data['image'])
        db.session.add(new_category)
        db.session.commit()
        return jsonify({"message": "Category added successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/admin/categories', methods=['GET'])
def get_categories():
    categories = ServiceCategory.query.all()
    categories_data = [{"id": category.id, "name": category.name} for category in categories]
    return jsonify(categories_data)

@app.route('/api/admin/addservices', methods=['POST'])
@jwt_required()
def add_service():
    data = request.json

    current_user = get_jwt_identity()

    # Check user role
    if current_user["role"] != ["admin"]:
        return {"error": "You are not authorized to perform this action."}, 401
    
    try:
        new_service = Service(
            name=data['name'],
            category_id=data['category_id'],
            base_price=data['base_price'],
            time_required=data['time_required'],
            description=data['description'],
            image_url=data['image_url']
        )
        db.session.add(new_service)
        db.session.commit()
        return jsonify({"message": "Service added successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/admin/service/<int:service_id>/update', methods=['PUT'])
@jwt_required()
def edit_service(service_id):
    data = request.json

    print(data)
    
    # Get the current user identity
    current_user = get_jwt_identity()

    # Authorization check
    if current_user["role"] != ["admin"]:
        return {"error": "You are not authorized to perform this action."}, 401

    # Fetch the service by ID
    service = db.session.get(Service, service_id)
    if not service:
        return {"error": "Service not found"}, 404

    # Validate and extract input data
    try:
        name = data["name"]
        base_price = data["base_price"]
        time_required = data["time_required"]
        description = data["description"]
        image_url = data.get("image_url")  # Optional
    except KeyError as e:
        return {"error": f"Missing field: {e.args[0]}"}, 400
    except TypeError:
        return {"error": "Invalid input format"}, 400

    # Update the service fields
    service.name = name
    service.base_price = base_price
    service.time_required = time_required
    service.description = description
    service.image_url = image_url
    service.created_at = datetime.now()  # updated_at

    # Commit changes to the database
    try:
        db.session.commit()
        return {"message": "Service updated successfully"}, 200
    except SQLAlchemyError as e:
        db.session.rollback()
        return {"error": "Database update failed", "details": str(e)}, 500

@app.route('/api/admin/service/<int:id>/delete', methods=['DELETE'])
@jwt_required()
def delete_service(id):
    current_user = get_jwt_identity()

    # Check user role
    if current_user["role"] != ["admin"]:
        return jsonify({"error": "You are not authorized to perform this action."}), 401
    
    try:
        # Fetch the service to delete
        service = db.session.get(Service, id)
        if not service:
            return jsonify({'error': 'Service not found'}), 404

        # Delete dependent ServiceRequestItems
        items = db.session.query(ServiceRequestItems).filter(ServiceRequestItems.service_id==id).all()

        for item in items:
            if item.service_request:
                db.session.delete(item.service_request)
            db.session.delete(item)
        
        # Delete dependent Bookings and their relations
        bookings = Bookings.query.filter_by(service_id=id).all()
        for booking in bookings:
            db.session.query(Remarks).filter_by(Bookings_id=booking.id).delete(synchronize_session=False)
            db.session.query(Payments).filter_by(booking_id=booking.id).delete(synchronize_session=False)
            db.session.query(BookingDetails).filter_by(booking_id=booking.id).delete(synchronize_session=False)

            db.session.delete(booking)
        db.session.query(CartRequests).filter_by(service_id=id).delete(synchronize_session=False)
        
        # Delete ServiceProfessional and the service itself
        professionals = db.session.query(ServiceProfessional).filter(ServiceProfessional.service_id==id).all()
        userIds = [professi.id for professi in professionals]

        for professional in professionals:
            if professional.addresses:
                db.session.delete(professional.addresses[0])
            db.session.delete(professional)
            

        for Id in userIds:
            db.session.delete(db.session.get(User,Id))

        db.session.delete(service)

        # Commit all changes
        db.session.commit()

        return jsonify({'message': 'Service deleted successfully'}), 200

    except Exception as e:
        # Rollback in case of errors
        print(e)
        db.session.rollback()
        return jsonify({'error': 'An internal error occurred. Please try again later.'}), 500

##########################################################################################################################################################



##########################################################################################################################################################
@app.route('/api/customer/bookings-count', methods=['GET'])
@jwt_required()
def get_booking_count():
    current_user = get_jwt_identity()

    # Check user role
    if current_user["role"] != ["customer"]:
        return {"error": "You are not authorized to perform this action."}, 401
    
    booking_id = Bookings.query.order_by(Bookings.id.desc()).first()
    if not booking_id:
       return jsonify({'id': 0}), 200
    else:
       return jsonify({'id':booking_id.id or 0}),200

@app.route('/api/customer/book-service', methods=['POST'])
@jwt_required()
def book_service():
    data = request.get_json()
    current_user = get_jwt_identity()

    # Check user role
    if current_user["role"] != ["customer"]:
        return {"error": "You are not authorized to perform this action."}, 401

    try:
        # Retrieve and validate booking details
        service_id = data.get('service_id')
        address_id = data.get('address_id')
        slot = data.get('slot')
        payment_details = data.get('payment_details')
        total_amount = round(float(data.get('total_amount')), 1)
        quantity = data.get('quantity')

        if not all([service_id, address_id, slot, quantity]):
            return jsonify({'error': 'All booking details are required.'}), 400

        # Parse slot date and time
        try:
            slot_date = slot.get('date')
            slot_time = slot.get('time')
            slot_datetime = datetime.strptime(f"{slot_date} {slot_time}", '%Y-%m-%d %I:%M %p')
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid date or time format for slot.'}), 400

        # Fetch service and address
        service = db.session.get(Service, service_id)
        if not service:
            return jsonify({'error': f'Invalid service: {service_id}'}), 403

        address = db.session.get(Address, address_id)
        if not address:
            return jsonify({'error': f'Invalid address: {address_id}'}), 405

        # Create Booking entry
        booking = Bookings(
            customer_id=current_user['id'],
            service_id=service_id,
            booking_date=datetime.now(),
            address_id=address_id,
            total_amount=total_amount,
            status='requested'
        )
        db.session.add(booking)
        db.session.flush()  # Get booking.id

        # Create BookingDetails entry
        booking_details = BookingDetails(
            booking_id=booking.id,
            quantity=quantity,
            date_of_slot_booked=slot_datetime
        )
        db.session.add(booking_details)

        # Process Payment entry
        payment = Payments(
            booking_id=booking.id,
            amount=total_amount,
            status='pending' if payment_details == 'cash' else 'completed',
            payment_method=payment_details,
            timestamp=datetime.now()
        )
        db.session.add(payment)

        # Query available professionals based on zip code
        professionals = (
            db.session.query(ServiceProfessional)
            .join(Address, Address.service_professional_id == ServiceProfessional.id)
            .filter(and_(Address.zip_code == address.zip_code, ServiceProfessional.service_id == service_id, ServiceProfessional.status=='Approved')).all()
        )

        # Check if professionals are available
        if not professionals:
            return jsonify({'error': 'No service professionals available in the selected area.'}), 404

        # Create ServiceRequest entries for each professional
        for professional in professionals:
            add_request = ServiceRequest(
                customer_id=current_user['id'],
                professional_id=professional.id,
                address_id=address.id,
                booking_id=booking.id,
                total_amount=round(total_amount * 0.8072, 1),  # Example calculation for adjusted amount
                status='requested'
            )
            db.session.add(add_request)
            db.session.flush()  # Get add_request.id

            add_request_details = ServiceRequestItems(
                service_request_id=add_request.id,
                service_id=service_id,
                scheduled_date=slot_datetime,
                quantity=quantity
            )
            db.session.add(add_request_details)

        # Remove service from the customer's cart
        cart = RequestingCart.query.filter_by(customer_id=current_user['id']).first()
        if cart:
            cart_item = CartRequests.query.filter_by(requests_cart_id=cart.id, service_id=service_id).first()
            if cart_item:
                db.session.delete(cart_item)

        # Commit transaction
        db.session.commit()
        return jsonify({'message': 'Booking successful', 'booking_id': booking.id}), 201

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'error': f'Database error occurred: {str(e)}'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'An error occurred: {str(e)}'}), 500

@app.route('/api/customer/booking/confirmation/<int:booking_id>', methods=['GET'])
@jwt_required()
def booking_confirmation(booking_id):
    current_user = get_jwt_identity()

    # Check user role
    if current_user["role"] != ["customer"]:
        return {"error": "You are not authorized to perform this action."}, 401
    
    try:
        # Fetch booking by ID
        booking = Bookings.query.filter_by(id=booking_id).first()
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        # Prepare booking details
        booking_details = {
            'booking_id': booking.id,
            'customer_name': booking.customer.fullname,
            'service_name': booking.service.name,
            'professional_name': booking.professional.fullname if booking.professional else "Not assigned",
            'address': {
                'location': booking.address.location,
                'city': booking.address.city,
                'state': booking.address.state,
                'zip_code': booking.address.zip_code
            } if booking.address else {},
            'total_amount': booking.total_amount,
            'status': booking.status,
            'booking_date': booking.booking_date.strftime('%Y-%m-%d %H:%M:%S'),
            'scheduled_date': booking.booking_details.date_of_slot_booked.strftime('%Y-%m-%d %H:%M:%S')
                if booking.booking_details else None
        }

        # Send JSON data for Vue.js frontend
        return jsonify(booking_details)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/editSlot', methods=['PUT'])
@jwt_required()
def edit_slot():
    try:
        # Parse JSON data from the request body
        data = request.get_json()
        slot = data.get('slot')
        booking_id = data.get('booking_id')

        # Validate input
        if not slot or not booking_id:
            return jsonify({"error": "Slot and booking_id are required"}), 401
        
        # Parse slot date and time
        try:
            slot_date = slot.get('date')
            slot_time = slot.get('time')
            slot_datetime = datetime.strptime(f"{slot_date} {slot_time}", '%Y-%m-%d %I:%M %p')
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid date or time format for slot'}), 400

        # Retrieve the booking to update
        booking = db.session.get(Bookings, booking_id)
        if not booking:
            return jsonify({"error": "Booking not found"}), 404

        # Update the slot in the BookingDetails table
        if booking.booking_details:
            booking.booking_details.date_of_slot_booked = slot_datetime
        else:
            return jsonify({"error": "Booking details not found"}), 404

        db.session.commit()

        return jsonify({"message": "Slot updated successfully"}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500

##########################################################################################################################################################



##########################################################################################################################################################

@app.route('/api/customer/services', methods=['GET'])
def customer_services():
    categories = ServiceCategory.query.all()
    data = []
    for category in categories:
        services = []
        for service in category.services:
            services.append({
                "id":service.id,
                "name":service.name,
                "price":service.base_price,
                "time":service.time_required,
                "description":service.description,
                "image_url":service.image_url,
            })
        data.append({
            "id":category.id,
            "name":category.name,
            "image_url":category.image_url,
            "services":services
        })
    return jsonify(data), 200

@app.route('/api/check-pincode/services', methods=['POST'])
def get_service_categories_by_pincode():
    data = request.get_json()
    pincode = data.get("pincode")
    
    # Ensure pincode is provided
    if not pincode:
        return jsonify({"error": "Pincode is required"}), 400

    try:
        # Query to find distinct service category IDs
        category_ids = ( db.session.query(Service.category_id).distinct()
            .join(ServiceProfessional, ServiceProfessional.service_id == Service.id)
            .join(Address, Address.service_professional_id == ServiceProfessional.id)
            .filter(Address.zip_code == pincode)
            .all()
        )
        
        # Extracting IDs from the query result
        category_id_list = [category_id[0] for category_id in category_ids]

        # Return the list of unique category IDs as JSON
        return jsonify({"service_category_ids": category_id_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/professionals', methods=['GET'])
@cache.cached(timeout=60)
def get_professionals():
    try:
        professionals = (
            db.session.query(
                ServiceProfessional.id,
                ServiceProfessional.fullname,
                ServiceProfessional.experience,
                Service.name.label("service_name"),
                ServiceProfessional.status.label("approval_status"),
                User.active.label("profile_status"),
                Address.zip_code.label("pincode"),
                ServiceProfessional.document_filename
            )
            .join(Service, ServiceProfessional.service_id == Service.id, isouter=True)
            .join(Address, Address.service_professional_id == ServiceProfessional.id)
            .join(User, ServiceProfessional.id == User.id)
            .all()
        )
        
        professional_list = [
            {
                "id": professional.id,
                "fullname": professional.fullname,
                "experience": professional.experience,
                "serviceName": professional.service_name,
                "approval_status": professional.approval_status,
                "profile_status": professional.profile_status,
                "pincode": professional.pincode,
                "document": professional.document_filename,
            }
            for professional in professionals
        ]

        profess = (
            db.session.query(ServiceProfessional)
            .outerjoin(Address, ServiceProfessional.id == Address.service_professional_id)
            .filter(and_(Address.zip_code == '835102', Address.service_professional_id != None))
            .all()
        )
        
        return jsonify(professional_list), 200
    except Exception as e:
        # Log the error and return a 500 error message
        print(f"Error fetching professionals: {e}")
        return jsonify({"error": "Failed to fetch professionals"}), 500

@app.route('/api/admin/check-pincode/professionals', methods=['POST'])
def get_professionals_by_pincode():
    data = request.get_json()
    pincode = data.get("pincode")
    
    if not pincode:
        return jsonify({"error": "Pincode is required"}), 400
    
    try:
        
        professional_ids = (db.session.query(ServiceProfessional.id).distinct()
                           .join(Address, Address.service_professional_id == ServiceProfessional.id)
            .filter(Address.zip_code == pincode)
            .all()
        )
        # Prepare the response
        professional_list = [professional_id[0] for professional_id in professional_ids]

        # Return the list of unique category IDs as JSON
        return jsonify({"professional_ids": professional_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/services', methods=['GET'])
def get_allservices():
    services = Service.query.all()
    services_data = [{
        "id": service.id,
        "name": service.name,
        "price": service.base_price,
        "time": service.time_required,
        "category": service.category.name,
        "description": service.description,
        "image": service.image_url
    } for service in services]

    return jsonify(services_data)

@app.route('/api/admin/check-pincode/services', methods=['POST'])
def get_services_by_pincode():
    data = request.get_json()
    pincode = data.get("pincode")
    
    # Ensure pincode is provided
    if not pincode:
        return jsonify({"error": "Pincode is required"}), 400

    try:
        # Query to find distinct service category IDs
        service_ids = ( db.session.query(Service.id).distinct()
            .join(ServiceProfessional, ServiceProfessional.service_id == Service.id)
            .join(Address, Address.service_professional_id == ServiceProfessional.id)
            .filter(Address.zip_code == pincode)
            .all()
        )
        
        # Extracting IDs from the query result
        service_id_list = [service_id[0] for service_id in service_ids]

        print(service_id_list)
        # Return the list of unique category IDs as JSON
        return jsonify({"service_ids": service_id_list}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/customers', methods=['GET'])
def get_customers():
    
    try:
        # Fetch all customers along with related user and address information
        customers = db.session.query(
            Customer.id,
            Customer.fullname,
            Customer.phone,
            Address.location,
            Address.zip_code.label("pincode"),
            User.active
        ).join(User, Customer.id == User.id) \
         .outerjoin(Address, Address.customer_id == Customer.id) \
         .all()

        # Format customers' data to return as JSON
        customer_list = [
            {
                "id": customer.id,
                "fullname": customer.fullname,
                "phone": customer.phone,
                "location": customer.location if customer.location else "N/A",
                "pincode": customer.pincode if customer.pincode else "N/A",
                "active": customer.active
            }
            for customer in customers
        ]
        
        return jsonify(customer_list), 200

    except Exception as e:
        print(f"Error retrieving customers: {e}")
        return jsonify({"error": "Failed to retrieve customers"}), 500

@app.route('/api/admin/check-pincode/customers', methods=['POST'])
def get_customers_by_pincode():

    pass

##########################################################################################################################################################



##########################################################################################################################################################

@app.route('/api/professional/requests', methods=['GET'])
@jwt_required()
def get_service_requests():
    current_user = get_jwt_identity()

    # Check user role
    if current_user["role"] != ["professional"]:
        return {"error": "You are not authorized to perform this action."}, 401
    
    professional = db.session.get(ServiceProfessional, current_user['id'])

    # Get search and date range parameters from query string
    search_query = request.args.get('searchQuery', '').lower()
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')

    # Query for service requests and join with related tables
    query = (
        db.session.query(
            ServiceRequest.id,
            Customer.fullname.label('name'),
            Customer.phone.label('mobileNo'),
            Service.id.label('service_id'),
            Service.name.label('serviceName'),
            ServiceRequestItems.quantity,
            BookingDetails.date_of_slot_booked.label('slotBooked'),
            BookingDetails.booking_id,
            ServiceRequest.total_amount.label('pay'),
            ServiceRequest.status,  # Add status field
            Address.location.label('location'),  # Customer location details
            Remarks.rating,  # Include rating from Remarks
        )
        .join(Customer, ServiceRequest.customer_id == Customer.id)
        .join(ServiceRequestItems, ServiceRequest.id == ServiceRequestItems.service_request_id)
        .join(Service, ServiceRequestItems.service_id == Service.id)
        .join(BookingDetails, BookingDetails.booking_id == ServiceRequest.booking_id)
        .join(Address, ServiceRequest.address_id == Address.id)  # Join with Address to get location details
        .outerjoin(Remarks, and_(
            Remarks.Bookings_id == ServiceRequest.booking_id,
            Remarks.professional_id == professional.id  # Match remarks for the current professional
        ))
        .filter(and_(Address.zip_code == professional.addresses[0].zip_code,
                     Service.id == professional.service_id, 
                     ServiceRequest.professional_id == current_user['id']))
    )

    # Apply search filter if search_query is provided
    if search_query:
        query = query.filter(
            (Customer.fullname.ilike(f'%{search_query}%')) |
            (Service.name.ilike(f'%{search_query}%'))
        )

    # Apply date filter if start_date or end_date is provided
    if start_date:
        query = query.filter(BookingDetails.date_of_slot_booked >= start_date)
    if end_date:
        query = query.filter(BookingDetails.date_of_slot_booked <= end_date)

    # Execute query and fetch results
    service_requests = query.all()

    # Convert query results into a list of dictionaries for JSON response
    result = [
        {
            'id': req.id,
            'booking_id': req.booking_id,
            'name': req.name,
            'mobileNo': req.mobileNo,
            'serviceName': req.serviceName,
            'quantity': req.quantity,
            'pay': req.pay,
            'slotBooked': req.slotBooked.strftime('%Y-%m-%d %H:%M:%S') if req.slotBooked else None,
            'status': req.status,  # Include status in result
            'rating': req.rating,  # Include rating in the result
            'location': req.location,  # Customer address details
        }
        for req in service_requests
    ]

    return jsonify(result)

@app.route('/api/professional/request/<int:request_id>/accept', methods=['PUT'])
@jwt_required()
def accept_request(request_id):
    current_user = get_jwt_identity()

    # Ensure the user is a professional
    if current_user["role"] != ["professional"]:
        return {"error": "You are not authorized to perform this action."}, 401

    try:
        # Find the service request by ID
        service_request = db.session.get(ServiceRequest, request_id)
        if not service_request:
            return jsonify({'error': 'Service request not found'}), 404

        # Update the request's status to 'accepted'
        service_request.status = 'accepted'

        # Find and delete other service requests with the same booking_id and 'requested' status
        service_requests = ServiceRequest.query.filter_by(
            booking_id=service_request.booking_id, 
            status='requested'
        ).all()

        for req in service_requests:
            if req.id != service_request.id:  # Skip the accepted request
                for item in req.items:  # Delete associated items
                    db.session.delete(item)
                db.session.delete(req)

        # Update the related booking status and assign the professional
        booking = db.session.get(Bookings, service_request.booking_id)
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404

        booking.status = 'accepted'
        booking.professional_id = current_user['id']

        # Commit the changes
        db.session.commit()

        return jsonify({'message': 'Request accepted and associated items deleted'}), 200

    except Exception as e:
        print(e)
        db.session.rollback()
        return jsonify({'error': 'An error occurred', 'details': str(e)}), 500

@app.route('/api/professional/request/<int:request_id>/reject', methods=['PUT'])
@jwt_required()
def reject_request(request_id):
    current_user = get_jwt_identity()

    # Ensure the user is a professional
    if current_user["role"] != ["professional"]:
        return {"error": "You are not authorized to perform this action."}, 401
    
    service_request = db.session.get(ServiceRequest, request_id)
    if not service_request:
        return jsonify({'error': 'Service request not found'}), 404

    service_request.status = 'rejected'
    db.session.commit()
    return jsonify({'message': 'Request rejected'}), 200

@app.route('/api/professional/request/<int:request_id>/working', methods=['PUT'])
@jwt_required()
def work_request(request_id):
    current_user = get_jwt_identity()

    # Ensure the user is a professional
    if current_user["role"] != ["professional"]:
        return {"error": "You are not authorized to perform this action."}, 401
    

    # Retrieve the ServiceRequest from the database
    service_request = db.session.get(ServiceRequest, request_id)

    if not service_request:
        # If the service request doesn't exist, return a 404 response
        return jsonify({'message': 'Service request not found'}), 404

    # Update the status of the service request to 'working'
    service_request.status = 'working'

    # Retrieve the related Booking
    booking = db.session.get(Bookings, service_request.booking_id)

    if not booking:
        # If the booking doesn't exist, return a 404 response
        return jsonify({'message': 'Booking not found'}), 404

    # Update the status of the booking to 'working'
    booking.status = 'working'

    try:
        # Commit the transaction to the database
        db.session.commit()
        return jsonify({'message': 'Started working on the request'}), 200
    except Exception as e:
        # If there's any error during the commit, rollback the transaction
        db.session.rollback()
        return jsonify({'message': f'Error updating request: {str(e)}'}), 500

@app.route('/api/professional/request/<int:request_id>/delete', methods=['DELETE'])
@jwt_required()
def delete_professional_request(request_id):
    current_user = get_jwt_identity()

    # Ensure the user is a professional
    if current_user["role"] != ["professional"]:
        return {"error": "You are not authorized to perform this action."}, 401

    try:
        service_request = db.session.get(ServiceRequest, request_id)

        if not service_request:
            return {"error": "Service request not found."}, 404


        if service_request.professional_id != current_user["id"]:
            return {"error": "You do not have permission to delete this request."}, 403

        for item in service_request.items:
            db.session.delete(item)

        booking= db.session.get(Bookings, service_request.booking_id)

        if booking and booking.status!='completed':
            booking.status='requested'

        db.session.delete(service_request)
        db.session.commit()

        return {"message": "Service request and related items deleted successfully."}, 200

    except Exception as e:
        db.session.rollback()
        return {"error": "An error occurred while deleting the service request.", "details": str(e)}, 500

@app.route('/api/requests/<int:booking_id>/close', methods=['POST'])
@jwt_required()
def close_request(booking_id):
    try:
        # Get the current user's ID
        current_user = get_jwt_identity()

        # Retrieve the booking record
        booking = db.session.get(Bookings, booking_id)

        if not booking:
            return jsonify({"error": "Booking not found"}), 404

        # Ensure the current user is the customer associated with the booking
        if booking.customer_id != current_user['id']:
            return jsonify({"error": "Unauthorized to close this booking"}), 403

        # Update the booking status to 'completed'
        booking.status = 'completed'

        # Update the booking's completion details
        booking_item = BookingDetails.query.filter_by(booking_id=booking.id).first()
        if booking_item:
            booking_item.date_of_completion = datetime.now()

        # Update the service request status to 'completed'
        service_request = ServiceRequest.query.filter_by(booking_id=booking.id).first()
        if service_request:
            service_request.status = 'completed'

            # Update all associated service request items
            service_request_items = ServiceRequestItems.query.filter_by(service_request_id=service_request.id).all()
            for item in service_request_items:
                item.completed_date = datetime.now()

        # Commit changes to the database
        db.session.commit()

        return jsonify({"message": "Booking and service requests marked as completed successfully"}), 200

    except SQLAlchemyError as e:
        # Rollback in case of a database error
        db.session.rollback()
        return jsonify({"error": "Database error", "details": str(e)}), 500

    except Exception as e:
        # General error handling
        return jsonify({"error": "An error occurred", "details": str(e)}), 500

@app.route('/api/submit-remark', methods=['POST'])
@jwt_required()
def submit_remark():
    current_user = get_jwt_identity()
    
    if current_user["role"] != ["customer"]:
        return {"error": "You are not supposed to do this!"}, 401
    
    # Extract and validate the input
    try:
        data = request.get_json()
        booking_id = data.get('booking_id')
        rating = data.get('rating')
        remark_text = data.get('remark')
        professional_id = data.get('professional_id')

        if not booking_id or not rating or not remark_text:
            return {"error": "Missing required fields"}, 400

        # Check if a remark already exists for this booking
        remarks = Remarks.query.filter_by(Bookings_id=booking_id).first()

        if remarks:
            # Update existing remark
            remarks.rating = rating
            remarks.remark = remark_text
            db.session.commit()
            return jsonify({"message": "Remark updated successfully"}), 200

        else:
            # Create new remark
            remark = Remarks(
                customer_id=current_user['id'],
                professional_id=professional_id,
                Bookings_id=booking_id,
                rating=rating,
                remark=remark_text
            )
            db.session.add(remark)
            db.session.commit()
            return jsonify({"message": "Remark submitted successfully"}), 200

    except SQLAlchemyError as e:
        db.session.rollback()
        print(f"Database error: {e}")
        return jsonify({"error": "Database error", "details": str(e)}), 500

    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred", "details": str(e)}), 500

@app.route('/api/requests/<int:request_id>', methods=['DELETE'])
def delete_request(request_id):
    # Find the service request by ID
    service_request = ServiceRequest.query.get(request_id)

    # Check if the service request exists
    if not service_request:
        return jsonify({'error': 'Service request not found'}), 404
    
    # Find all service request items associated with this service request
    service_request_items = ServiceRequestItems.query.filter_by(service_request_id=service_request.id).all()

    # Check if there are service request items to delete
    if not service_request_items:
        return jsonify({'error':'Service Request Items not found'}), 404

    # Delete all associated service request items
    for item in service_request_items:
        db.session.delete(item)
    
    # Delete the service request itself
    db.session.delete(service_request)
    
    # Commit the changes to the database
    db.session.commit()

    # Return a success message
    return jsonify({'message': 'Request and associated items deleted'}), 200

##########################################################################################################################################################



##########################################################################################################################################################
def generate_service_requests_csv():
    # Query all completed service requests
    completed_requests = ServiceRequest.query.filter_by(status='completed').all()

    csv_buffer = io.StringIO()
    csv_writer = csv.writer(csv_buffer)

    # Write header row
    csv_writer.writerow([
        'Service ID', 'Customer ID', 'Professional ID',
        'Date of Request', 'Remarks', 'Rating',
        'Completion Date', 'Professional Earnings', 
        'Total Booking Amount', 'Status'
    ])

    # Write details for each request
    for request in completed_requests:
        # Fetch remarks associated with the request (if any)
        remarks = Remarks.query.filter_by(Bookings_id=request.booking_id).first()
        rating = remarks.rating if remarks else ''
        remark_text = remarks.remark if remarks else ''

        # Fetch the booking associated with this service request
        booking = Bookings.query.filter_by(id=request.booking_id).first()
        total_booking_amount = booking.total_amount if booking else ''

        csv_writer.writerow([
            request.id,
            request.customer_id,
            request.professional_id,
            request.requested_date.strftime('%Y-%m-%d %H:%M:%S'),
            remark_text,
            rating,
            request.items[0].completed_date.strftime('%Y-%m-%d %H:%M:%S') if request.items else '',
            request.total_amount,
            total_booking_amount,
            request.status
        ])

    return csv_buffer.getvalue()

@app.route('/admin/export-service-requests', methods=['GET'])
@jwt_required()
def export_service_requests():
    current_user = get_jwt_identity()
    if current_user["role"] != ["admin"]:
        return {"error": "You are not supposed to do this!"}, 401

    try:
        csv_data = generate_service_requests_csv()
        task.export_service_requests.delay(csv_data)
        return Response(
            csv_data,
            mimetype='text/csv',
            headers={
                'Content-Disposition': 'attachment;filename=service_requests_export.csv'
            }
        )
    
    except Exception as e:
        print(e)
        return {"error": str(e)}, 500

##########################################################################################################################################################

@app.route('/clear_cache', methods=['POST'])
def clear_cache():
    cache.clear()
    return jsonify({'message': 'Cache cleared successfully'}), 200

if __name__ == "__main__":
    app.run(debug=True, host='127.0.0.1', port=5000)