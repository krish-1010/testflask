from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://root:Eshwar%402004@localhost/employee'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'your_secret_key'  # For session management

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# User Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

# Create Tables
with app.app_context():
    db.create_all()

# Home Page
@app.route('/')
def home():
    return render_template('index.html')

# Registration Page
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        data = request.form
        hashed_password = bcrypt.generate_password_hash(data['password']).decode('utf-8')
        new_user = User(username=data['username'], password_hash=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

# Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.form
        user = User.query.filter_by(username=data['username']).first()
        if user and bcrypt.check_password_hash(user.password_hash, data['password']):
            session['user_id'] = user.id  # Store user ID in session
            return redirect(url_for('dashboard'))
        return jsonify({'message': 'Invalid credentials'}), 401
    return render_template('login.html')

# Protected Dashboard
@app.route('/dashboard', methods=['GET'])
def dashboard():
    if 'user_id' not in session:  # Check if user is logged in
        return redirect(url_for('login'))  # Redirect to login page if not authenticated

    user = User.query.get(session['user_id'])
    return render_template('user_dashboard.html', username=user.username)

# Logout Route
@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Remove user_id from session
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
