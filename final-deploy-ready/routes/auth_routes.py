from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database.db import get_db_connection

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.admin_dashboard'))
        return redirect(url_for('student.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        student_code = request.form.get('student_code', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        department = request.form.get('department', '').strip()
        semester = request.form.get('semester', '1').strip()

        if not all([student_code, full_name, email, password, department]):
            flash('All required fields must be completed.', 'danger')
            return render_template('register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return render_template('register.html')

        conn = get_db_connection()
        if not conn:
            flash('Database connection failed. Please verify MySQL service status.', 'danger')
            return render_template('register.html')

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT id FROM students WHERE email = %s OR student_code = %s", (email, student_code))
            if cursor.fetchone():
                flash('An account with this email or Student ID already exists.', 'danger')
                return render_template('register.html')

            pw_hash = generate_password_hash(password)
            cursor.execute(
                """INSERT INTO students (student_code, full_name, email, password_hash, department, semester, role)
                   VALUES (%s, %s, %s, %s, %s, %s, 'student')""",
                (student_code, full_name, email, pw_hash, department, int(semester))
            )
            conn.commit()
            flash('Registration successful. Please sign in with your credentials.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            conn.rollback()
            flash(f'Registration error: {str(e)}', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        conn = get_db_connection()
        if not conn:
            flash('Database connection error. Check server configuration.', 'danger')
            return render_template('login.html')

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
            user = cursor.fetchone()

            if user and check_password_hash(user['password_hash'], password):
                session.clear()
                session['user_id'] = user['id']
                session['full_name'] = user['full_name']
                session['role'] = user['role']
                session['student_code'] = user['student_code']

                if user['role'] == 'admin':
                    return redirect(url_for('admin.admin_dashboard'))
                return redirect(url_for('student.dashboard'))
            else:
                flash('Invalid email address or password.', 'danger')
        finally:
            cursor.close()
            conn.close()

    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out securely.', 'info')
    return redirect(url_for('auth.login'))