import os
from flask import Flask
from werkzeug.security import generate_password_hash
from config import Config
from database.db import get_db_connection
from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from routes.admin_routes import admin_bp

def ensure_default_admin():
    admin_password = os.getenv('ADMIN_PASSWORD')
    if not admin_password:
        return
    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM students WHERE email = %s", ('admin@system.edu',))
        admin = cursor.fetchone()
        valid_hash = generate_password_hash(admin_password)
        if not admin:
            cursor.execute("""
                INSERT INTO students (student_code, full_name, email, password_hash, department, semester, education_details, role)
                VALUES ('ADMIN-001', 'System Administrator', 'admin@system.edu', %s, 'Administration', 0, 'System Admin', 'admin')
            """, (valid_hash,))
        else:
            cursor.execute("UPDATE students SET password_hash = %s WHERE email = 'admin@system.edu'", (valid_hash,))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"[Startup Admin Check Warning]: {e}")
    finally:
        conn.close()

def ensure_resume_extractions_table():
    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_resume_extractions (
                student_id INT PRIMARY KEY,
                original_filename VARCHAR(255) NOT NULL,
                extracted_text MEDIUMTEXT,
                extracted_skills JSON NOT NULL,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"[Resume Table Startup Warning]: {e}")
    finally:
        conn.close()

def ensure_student_projects_table():
    conn = get_db_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS student_projects (
                id INT AUTO_INCREMENT PRIMARY KEY,
                student_id INT NOT NULL,
                title VARCHAR(150) NOT NULL,
                github_url VARCHAR(500),
                technologies VARCHAR(255) NOT NULL,
                description TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
            )
        """)
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"[Student Projects Table Startup Warning]: {e}")
    finally:
        conn.close()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    app.register_blueprint(auth_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(admin_bp)

    with app.app_context():
        ensure_default_admin()
        ensure_resume_extractions_table()
        ensure_student_projects_table()

    return app

if __name__ == '__main__':
    application = create_app()
    application.run(debug=True, host='127.0.0.1', port=5000)