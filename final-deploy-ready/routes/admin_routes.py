from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from database.db import get_db_connection

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash('Administrator privileges required.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/dashboard')
@admin_required
def admin_dashboard():
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return render_template('admin.html', stats={}, students=[], skills=[], careers=[], mappings=[], assessments=[])

    try:
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS cnt FROM students WHERE role = 'student'")
        total_students = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM assessments")
        total_assessments = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM skills")
        total_skills = cursor.fetchone()['cnt']

        cursor.execute("SELECT COUNT(*) AS cnt FROM careers")
        total_careers = cursor.fetchone()['cnt']

        cursor.execute("""
            SELECT id, student_code, full_name, email, department, semester, created_at
            FROM students WHERE role = 'student' ORDER BY created_at DESC
        """)
        students = cursor.fetchall()

        cursor.execute("""
            SELECT a.id, s.student_code, s.full_name, a.average_score, a.taken_at
            FROM assessments a
            JOIN students s ON a.student_id = s.id
            ORDER BY a.taken_at DESC LIMIT 25
        """)
        assessments = cursor.fetchall()

        cursor.execute("SELECT * FROM skills ORDER BY id ASC")
        skills = cursor.fetchall()

        cursor.execute("SELECT * FROM careers ORDER BY id ASC")
        careers = cursor.fetchall()

        cursor.execute("""
            SELECT crs.id, c.title AS career_title, s.name AS skill_name, crs.required_proficiency, crs.weight
            FROM career_required_skills crs
            JOIN careers c ON crs.career_id = c.id
            JOIN skills s ON crs.skill_id = s.id
            ORDER BY c.title ASC, s.name ASC
        """)
        mappings = cursor.fetchall()

        cursor.close()
        stats = {
            'total_students': total_students,
            'total_assessments': total_assessments,
            'total_skills': total_skills,
            'total_careers': total_careers
        }
        return render_template(
            'admin.html',
            stats=stats,
            students=students,
            assessments=assessments,
            skills=skills,
            careers=careers,
            mappings=mappings
        )
    finally:
        conn.close()

@admin_bp.route('/skills/add', methods=['POST'])
@admin_required
def add_skill():
    name = request.form.get('name', '').strip()
    category = request.form.get('category', '').strip()
    description = request.form.get('description', '').strip()

    if not name or not category:
        flash('Skill name and category are required.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("INSERT INTO skills (name, category, description) VALUES (%s, %s, %s)", (name, category, description))
        conn.commit()
        cursor.close()
        flash(f'Skill "{name}" added successfully.', 'success')
    except Exception as e:
        flash(f'Could not add skill: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/skills/delete/<int:skill_id>', methods=['POST'])
@admin_required
def delete_skill(skill_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM skills WHERE id = %s", (skill_id,))
        conn.commit()
        cursor.close()
        flash('Skill deleted from catalog.', 'info')
    finally:
        conn.close()
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/careers/add', methods=['POST'])
@admin_required
def add_career():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    industry_outlook = request.form.get('industry_outlook', '').strip()

    if not title or not description:
        flash('Career title and description are required.', 'danger')
        return redirect(url_for('admin.admin_dashboard'))

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO careers (title, description, industry_outlook) VALUES (%s, %s, %s)",
            (title, description, industry_outlook)
        )
        conn.commit()
        cursor.close()
        flash(f'Career profile "{title}" created.', 'success')
    except Exception as e:
        flash(f'Error creating career profile: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/mappings/save', methods=['POST'])
@admin_required
def save_career_skill_mapping():
    career_id = request.form.get('career_id', type=int)
    skill_id = request.form.get('skill_id', type=int)
    required_proficiency = request.form.get('required_proficiency', type=int)
    weight = request.form.get('weight', type=float, default=1.0)

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO career_required_skills (career_id, skill_id, required_proficiency, weight)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                required_proficiency = VALUES(required_proficiency),
                weight = VALUES(weight)
        """, (career_id, skill_id, required_proficiency, weight))
        conn.commit()
        cursor.close()
        flash('Career skill requirement updated.', 'success')
    except Exception as e:
        flash(f'Mapping error: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/mappings/delete/<int:mapping_id>', methods=['POST'])
@admin_required
def delete_mapping(mapping_id):
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM career_required_skills WHERE id = %s", (mapping_id,))
        conn.commit()
        cursor.close()
        flash('Career requirement removed.', 'info')
    finally:
        conn.close()
    return redirect(url_for('admin.admin_dashboard'))