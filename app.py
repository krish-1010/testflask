from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from flask import send_from_directory
#from flask import jsonify
from datetime import datetime,timedelta
from flask_migrate import Migrate  # ✅ Import Flask-Migrate
import os
import random
#import pandas as pd
from werkzeug.utils import secure_filename


app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Use a strong secret key

# ✅ Configure Upload Folder
UPLOAD_FOLDER = 'static/submissions'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ✅ Ensure the directory exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# ✅ Function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Ensure Flask correctly serves static files
app._static_folder = os.path.abspath("static")

# Database Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///./users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
migrate = Migrate(app, db)  # ✅ Add this line
bcrypt = Bcrypt(app)

# Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USERNAME'] = 'prasadthimi@gmail.com'
app.config['MAIL_PASSWORD'] = 'czox putd gnle rnyj'
mail = Mail(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), nullable=False)

    # Relationship: A user can have multiple projects
       # Relationship: A user (employee) can have multiple assigned projects
    projects = db.relationship('Project', back_populates='user', 
                               foreign_keys='Project.user_id', 
                               cascade="all, delete-orphan")

    # Relationship: Admin can assign multiple projects
    assigned_projects = db.relationship('Project', foreign_keys='Project.assigned_by',
                                        back_populates='assigned_by_user')

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    duration = db.Column(db.Integer, nullable=True)  # Duration in minutes
    status = db.Column(db.String(50), nullable=False, default="pending")
    deadline = db.Column(db.DateTime, nullable=False)  # ✅ Changed to DateTime
    start_time = db.Column(db.DateTime, nullable=True)
    end_time = db.Column(db.DateTime, nullable=True)
    file_path = db.Column(db.String(255), nullable=True)  # ✅ Store submitted file path

    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    assigned_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Admin who assigned

    # Relationship: A project belongs to a user (employee)
    user = db.relationship('User', back_populates='projects', foreign_keys=[user_id])

    # Relationship: Admin who assigned the project
    assigned_by_user = db.relationship('User', foreign_keys=[assigned_by])

    def calculate_duration(self):
        if self.start_time and self.end_time:
            # Duration in minutes
            return (self.end_time - self.start_time).total_seconds() / 60
        return 0  # Return 0 if duration cannot be calculated

    # Update duration when the project is done
    def update_duration(self):
        if self.status in ['done', 'doing'] and self.start_time and self.end_time:
            self.duration = self.calculate_duration()
            db.session.commit()  # Commit changes to the database

    # ✅ NEW: Check if a project is overdue
    def is_overdue(self):
        """Returns True if the project is overdue and not completed."""
        return self.status not in ["complete"] and datetime.utcnow() > self.deadline


# Create tables
with app.app_context():
    db.create_all()


# Manually serve static files if needed
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)


# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    role = request.args.get('role')
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            session['user'] = email
            session['role'] = user.role  # Store role in session
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'employee':
                return redirect(url_for('employee_dashboard'))
        flash("Invalid credentials, please try again", "error")
    return render_template('login.html', role=role)

# Signup Route
# Signup Route
## Signup Route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    role = request.args.get('role')  # Get the role passed in the URL
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email is already registered, please use another email.", "error")
            return render_template('signup.html', role=role)

        # Ensure password and confirm password match
        if password != confirm_password:
            flash("Passwords do not match!", "error")
            return render_template('signup.html', role=role)

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Create a new user with the role (admin or employee)
        new_user = User(name=name, email=email, password=hashed_password, role=role)

        # Add the new user to the database
        db.session.add(new_user)
        db.session.commit()

        flash(f"Account created successfully as {role}!", "success")
        return redirect(url_for('login_page', role=role))  # Pass the role in the URL

    return render_template('signup.html', role=role)

# Admin Dashboard Route
# Admin Dashboard Route
@app.route('/admin-dashboard')
def admin_dashboard():
    if 'user' not in session:
        return redirect(url_for('login_page'))
    
    user = User.query.filter_by(email=session['user']).first()
    
    if not user or user.role != 'admin':
        flash("You are not authorized to access the admin dashboard.", "error")
        return redirect(url_for('login_page'))
    
    # Get all employees
    employees = User.query.filter_by(role='employee').all()

    # Prepare the table data
    employee_data = []
    employee_performance = []  # For "Top Employees"

    for employee in employees:
        projects_done = Project.query.filter_by(user_id=employee.id, status='complete').count()
        projects_pending = Project.query.filter_by(user_id=employee.id, status='pending').count()
        projects_doing = Project.query.filter_by(user_id=employee.id, status='doing').count()

        # ✅ Count overdue projects
        projects_overdue = sum(1 for project in employee.projects if project.is_overdue())

        # Calculate total time spent on completed projects
        completed_projects = [project for project in employee.projects if project.status == 'complete']
        total_time_spent = sum(project.duration for project in completed_projects if project.duration)

        # ✅ Calculate average time spent per project
        avg_time_spent = (total_time_spent / len(completed_projects)) if completed_projects else float('inf')

        # Add employee data for the main table
        employee_data.append({
            'id': employee.id,
            'name': employee.name,
            'email': employee.email,
            'projects_done': projects_done,
            'projects_pending': projects_pending,
            'projects_doing': projects_doing,
            'projects_overdue': projects_overdue,  # ✅ Added overdue count
            'total_time_spent': total_time_spent,
            'projects': employee.projects  # Include all the projects to display in the table
        })

        # ✅ Add to performance list for ranking
        if projects_done > 0:  # Only consider employees who completed at least one project
            employee_performance.append({
                'name': employee.name,
                'projects': projects_done,
                'avg_time': avg_time_spent
            })

    # ✅ Sort employees based on performance (most projects, least avg time)
    top_employees = sorted(employee_performance, key=lambda x: (-x['projects'], x['avg_time']))[:5]  # Top 5 employees

    return render_template('admin_dashboard.html', admin_name=user.name, employee_data=employee_data, top_employees=top_employees)


# Employee Dashboard Route

# Employee Dashboard Route
@app.route('/employee-dashboard', methods=['GET', 'POST'])
def employee_dashboard():
    if 'user' not in session:
        return redirect(url_for('login_page'))

    user = User.query.filter_by(email=session['user']).first()

    if not user or user.role != 'employee':
        flash("Unauthorized access.", "error")
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        title = request.form.get('title')
        deadline = request.form.get('deadline')

        if not title or not deadline:
            flash("Please fill all required fields!", "error")
            return redirect(url_for('employee_dashboard'))

        try:
            deadline_date = datetime.strptime(deadline, "%Y-%m-%d").date()  # Convert string to date
        except ValueError:
            flash("Invalid date format!", "error")
            return redirect(url_for('employee_dashboard'))

        if deadline_date < datetime.today().date():
            flash("Deadline must be a future date!", "error")
            return redirect(url_for('employee_dashboard'))

        new_project = Project(
            title=title,
            status="pending",
            deadline=deadline_date,  # Ensure it's stored as a date
            start_time=None,
            end_time=None,
            duration=None,
            user_id=user.id,
            assigned_by=None  # Employee added their own project
        )

        db.session.add(new_project)
        db.session.commit()

        flash("Project added successfully!", "success")
        return redirect(url_for('employee_dashboard'))

    projects = Project.query.filter_by(user_id=user.id).all()

    # 🔹 Ensure all deadlines are converted to `datetime.date` before comparison
    for project in projects:
        if isinstance(project.deadline, str):  # If deadline is stored as a string, convert it
            try:
                project.deadline = datetime.strptime(project.deadline, "%Y-%m-%d").date()
            except ValueError:
                project.deadline = None  # Handle invalid format safely

    current_date = datetime.today().date()  # Used for overdue status in HTML

    return render_template('employee_dashboard.html', user=user, projects=projects, current_date=current_date)

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()
        if user:
            otp = random.randint(100000, 999999)
            session['otp'] = otp
            session['email'] = email 
            msg = Message("OTP for Password Reset", sender=app.config['MAIL_USERNAME'], recipients=[email])
            msg.body = f"Your OTP is: {otp}"
            mail.send(msg)
            flash("OTP sent to your email", "info")
            return redirect(url_for('reset_password'))
        flash("Email not found", "error")
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        otp = request.form['otp']
        new_password = request.form['new_password']

        if otp == str(session.get('otp')):  # Validate OTP
            email = session.get('email')  # Get email from session
            user = User.query.filter_by(email=email).first()

            if user:  # Ensure user exists before updating password
                hashed_password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                user.password = hashed_password
                db.session.commit()

                flash("Password reset successful!", "success")

                # Clear session data after reset
                session.pop('otp', None)
                session.pop('email', None)

                # ✅ Redirect based on user role
                if user.role == "employee":
                    return redirect(url_for('login', role="employee"))
                else:
                    return redirect(url_for('login', role="admin"))

        flash("Invalid OTP or session expired!", "error")

    return render_template('reset_password.html')



@app.route('/login-page', methods=['GET'])
def login_page():
    # Get the role parameter from the URL (admin or employee)
    role = request.args.get('role')
    return render_template('login.html', role=role)


# ✅ Start Project
@app.route('/start-project/<int:project_id>', methods=['GET'])
def start_project(project_id):
    project = Project.query.get_or_404(project_id)

    if project.start_time is None:  # Prevent overriding
        project.start_time = datetime.now()
        project.status = 'doing'
        db.session.commit()
        flash("Project started!", "success")
    else:
        flash("Project is already started!", "info")

    return redirect(url_for('employee_dashboard'))

# ✅ Employee Submits File to End Project
@app.route('/submit-project/<int:project_id>', methods=['POST'])
def submit_project(project_id):
    project = Project.query.get_or_404(project_id)

    # ✅ Check if a file is uploaded
    if 'file' not in request.files:
        flash("No file uploaded!", "error")
        return redirect(url_for('employee_dashboard'))

    file = request.files['file']

    # ✅ Ensure a file is selected
    if file.filename == '':
        flash("No selected file!", "error")
        return redirect(url_for('employee_dashboard'))

    # ✅ Check file type
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}
    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    if not allowed_file(file.filename):
        flash("Invalid file type! Allowed: txt, pdf, docx.", "error")
        return redirect(url_for('employee_dashboard'))

    # ✅ Ensure upload directory exists
    UPLOAD_FOLDER = os.path.join("static", "submissions")
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)

    # ✅ Secure filename & Save file
    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    # ✅ Store filename (not full path) in database
    project.file_path = filename
    project.end_time = datetime.now()
    project.duration = (project.end_time - project.start_time).total_seconds() / 3600
    project.status = 'pending_review'

    db.session.commit()

    flash("File submitted for review!", "success")
    return redirect(url_for('employee_dashboard'))




# ✅ Admin Reviews the Submitted Project
@app.route('/review-project/<int:project_id>/<action>', methods=['POST'])
def review_project(project_id, action):
    project = Project.query.get_or_404(project_id)

    if action == 'approve':
        project.status = 'complete'
        flash("Project approved and marked as complete!", "success")
    elif action == 'reject':
        project.status = 'reassigned'
        project.start_time = None  # Reset project
        project.end_time = None
        project.duration = None
        flash("Project rejected and reassigned!", "error")

    db.session.commit()
    return redirect(url_for('admin_dashboard'))


# ✅ Set Deadline
@app.route('/set-deadline/<int:project_id>', methods=['POST'])
def set_deadline(project_id):
    project = Project.query.get_or_404(project_id)
    deadline = request.form.get('deadline')

    if deadline:
        project.deadline = deadline
        db.session.commit()
        flash("Deadline set successfully!", "success")
    else:
        flash("Invalid deadline!", "error")

    return redirect(url_for('employee_dashboard'))
@app.route('/logout')
def logout():
    session.pop('user', None)
    flash("You have been logged out.", "success")
    return redirect(url_for('login_page'))  # Redirect to login page

@app.route('/add_project', methods=['POST'])
def add_project():
    title = request.form.get('title')
    deadline = request.form.get('deadline')
    user_id = request.form.get('user_id')

    if not title or not deadline:
        flash('Please provide all required fields', 'error')
        return redirect(url_for('employee_dashboard'))

    new_project = Project(
        title=title,
        deadline=deadline,
        start_time=datetime.now(),  # Add default start time
        status="Pending",
        user_id=session['user_id']
    )
    
    db.session.add(new_project)
    db.session.commit()
    
    flash('Project added successfully!', 'success')
    return redirect(url_for('employee_dashboard'))



@app.route('/assign-project/<int:employee_id>', methods=['GET', 'POST'])
def assign_project(employee_id):
    if 'user' not in session:
        return redirect(url_for('login_page'))

    admin = User.query.filter_by(email=session['user']).first()
    if admin.role != 'admin':
        flash("Unauthorized access.", "error")
        return redirect(url_for('admin_dashboard'))

    employee = User.query.get_or_404(employee_id)

    if request.method == 'POST':
        title = request.form['title']
        deadline_str = request.form['deadline']

        if not title or not deadline_str:
            flash("All fields are required!", "error")
            return redirect(url_for('assign_project', employee_id=employee_id))
        try:
            # Convert the deadline string to a datetime object
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d')
        except ValueError:
            flash("Invalid date format. Please use YYYY-MM-DD.", "error")
            return redirect(url_for('assign_project', employee_id=employee_id))

        new_project = Project(
            title=title,
            status="pending",
            deadline=deadline,
            start_time=None,
            end_time=None,
            duration=None,
            user_id=employee.id,
            assigned_by=admin.id  # Track who assigned the project
        )
        db.session.add(new_project)
        db.session.commit()

        flash("Project assigned successfully!", "success")
        return redirect(url_for('admin_dashboard'))

    return render_template('assign_project.html', employee=employee)


#employeeperformance
@app.route('/employee_performance/<int:employee_id>')
def employee_performance(employee_id):
    employee = User.query.get(employee_id)
    if not employee:
        flash("Employee not found", "danger")
        return redirect(url_for('admin_dashboard'))

    # Get project data for charts
    completed = Project.query.filter_by(user_id=employee_id, status="complete").count()
    pending = Project.query.filter_by(user_id=employee_id, status="pending").count()
    in_progress = Project.query.filter_by(user_id=employee_id, status="doing").count()
     # Get overdue projects
    overdue = sum(1 for project in employee.projects if project.is_overdue())  # Check overdue projects
    
    project_counts = [completed, pending, in_progress,overdue]
    project_titles = [p.title for p in employee.projects]
    project_durations = [p.duration or 0 for p in employee.projects]
    
    return render_template('employee_performance.html', 
                           employee=employee, 
                           project_counts=project_counts, 
                           project_titles=project_titles, 
                           project_durations=project_durations)



#download
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)

@app.route('/clear-session')
def clear_session():
    session.clear()
    return "Session cleared!"
    
if __name__ == '__main__':
    app.run(debug=True,use_reloader=False)
