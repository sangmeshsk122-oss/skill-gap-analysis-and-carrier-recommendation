import json
from urllib.parse import urlparse
from functools import wraps
from flask import Blueprint, abort, current_app, render_template, request, redirect, url_for, session, flash, jsonify, send_file
from database.db import get_db_connection
from services.analysis_service import (
    compute_career_analysis,
    compute_skill_priority_ranking,
    get_curriculum_details
)
from services.pdf_service import generate_student_report_pdf
from services.progress_service import build_skill_progress
from services.resume_service import ResumeExtractionError, extract_resume_text, extract_skill_matches
from services.question_service import (
    FIXED_QUESTION_BANK_VERSION,
    QuestionBankError,
    get_fixed_questions,
    score_answers,
    validate_questions
)

student_bp = Blueprint('student', __name__, url_prefix='/student')

SKILL_LEVELS = {
    1: 'Beginner',
    2: 'Basic',
    3: 'Intermediate',
    4: 'Advanced',
    5: 'Expert'
}
QUESTIONS_PER_LEVEL = 20

def is_valid_github_url(value):
    if not value:
        return True
    parsed = urlparse(value)
    hostname = (parsed.hostname or '').lower()
    return parsed.scheme in ('http', 'https') and (
        hostname == 'github.com' or hostname.endswith('.github.com')
    )

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'student':
            flash('Please log in as a student to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def fetch_student_context(conn, student_id):
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()

    cursor.execute("""
        SELECT s.id, s.name, s.category, s.description,
               COALESCE(progress.highest_level_passed, 0) AS proficiency
        FROM skills s
        LEFT JOIN student_skill_progress progress
            ON s.id = progress.skill_id AND progress.student_id = %s
        ORDER BY s.id ASC
    """, (student_id,))
    skills = cursor.fetchall()

    cursor.execute("SELECT * FROM careers ORDER BY id ASC")
    careers = cursor.fetchall()
    for c in careers:
        cursor.execute("""
            SELECT crs.skill_id, s.name AS skill_name, crs.required_proficiency, crs.weight
            FROM career_required_skills crs
            JOIN skills s ON crs.skill_id = s.id
            WHERE crs.career_id = %s
        """, (c['id'],))
        c['required_skills'] = cursor.fetchall()

    cursor.close()
    return student, skills, careers

def fetch_portfolio_skill_names(conn, student_id):
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT technologies FROM student_projects WHERE student_id = %s",
            (student_id,)
        )
        return {
            technology.strip().casefold()
            for project in cursor.fetchall()
            for technology in (project['technologies'] or '').split(',')
            if technology.strip()
        }
    finally:
        cursor.close()

@student_bp.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return render_template('dashboard.html', has_assessment=False)

    try:
        student, skills, careers = fetch_student_context(conn, session['user_id'])
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT COUNT(*) AS count FROM assessments WHERE student_id = %s", (session['user_id'],))
        assessment_count = cursor.fetchone()['count']

        cursor.execute("SELECT status, COUNT(*) AS cnt FROM learning_roadmaps WHERE student_id = %s GROUP BY status", (session['user_id'],))
        roadmap_stats = {row['status']: row['cnt'] for row in cursor.fetchall()}
        cursor.close()

        has_assessment = any(skill['proficiency'] > 0 for skill in skills)
        skill_map = {s['id']: s['proficiency'] for s in skills}
        portfolio_skill_names = fetch_portfolio_skill_names(conn, session['user_id'])
        analysis = compute_career_analysis(
            skill_map, careers, portfolio_skill_names
        ) if has_assessment else []
        top_career = analysis[0] if analysis else None
        avg_proficiency = round(sum(s['proficiency'] for s in skills) / len(skills), 2) if skills else 0

        return render_template(
            'dashboard.html',
            student=student,
            skills=skills,
            has_assessment=has_assessment,
            assessment_count=assessment_count,
            avg_proficiency=avg_proficiency,
            top_career=top_career,
            analysis=analysis,
            roadmap_stats=roadmap_stats
        )
    finally:
        conn.close()

@student_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('student.dashboard'))

    try:
        cursor = conn.cursor(dictionary=True)
        if request.method == 'POST':
            full_name = request.form.get('full_name', '').strip()
            department = request.form.get('department', '').strip()
            semester = int(request.form.get('semester', 1))
            education_details = request.form.get('education_details', '').strip()
            career_interests = request.form.get('career_interests', '').strip()

            cursor.execute("""
                UPDATE students
                SET full_name = %s, department = %s, semester = %s, education_details = %s, career_interests = %s
                WHERE id = %s
            """, (full_name, department, semester, education_details, career_interests, session['user_id']))
            conn.commit()
            session['full_name'] = full_name
            flash('Student profile updated successfully.', 'success')

        cursor.execute("SELECT * FROM students WHERE id = %s", (session['user_id'],))
        student = cursor.fetchone()

        cursor.execute("""
            SELECT s.id, s.name, s.category,
                   COALESCE(progress.highest_level_passed, 0) AS proficiency
            FROM skills s
            LEFT JOIN student_skill_progress progress
                ON s.id = progress.skill_id AND progress.student_id = %s
            ORDER BY s.id ASC
        """, (session['user_id'],))
        skills = cursor.fetchall()

        cursor.execute("""
            SELECT original_filename, extracted_skills, uploaded_at
            FROM student_resume_extractions
            WHERE student_id = %s
        """, (session['user_id'],))
        resume = cursor.fetchone()

        resume_matches = []
        if resume:
            raw_matches = resume['extracted_skills']
            if isinstance(raw_matches, str):
                try:
                    raw_matches = json.loads(raw_matches)
                except json.JSONDecodeError:
                    raw_matches = []
            resume_matches = raw_matches if isinstance(raw_matches, list) else []

        cursor.execute("""
            SELECT id, title, github_url, technologies, description, created_at
            FROM student_projects
            WHERE student_id = %s
            ORDER BY created_at DESC, id DESC
        """, (session['user_id'],))
        projects = cursor.fetchall()

        resume_skill_ids = {
            item.get('skill_id') for item in resume_matches
            if isinstance(item, dict) and item.get('skill_id') is not None
        }
        resume_comparison = []
        for skill in skills:
            in_resume = skill['id'] in resume_skill_ids
            in_assessment = skill['proficiency'] > 0
            if in_resume and in_assessment:
                status = 'Aligned'
            elif in_resume:
                status = 'Resume Only'
            elif in_assessment:
                status = 'Assessment Only'
            else:
                status = 'Not Evidenced'
            project_evidence = []
            for project in projects:
                technologies = [
                    item.strip().lower()
                    for item in (project['technologies'] or '').split(',')
                    if item.strip()
                ]
                if skill['name'].lower() in technologies:
                    project_evidence.append(project['title'])
            resume_comparison.append({
                'skill_name': skill['name'],
                'category': skill['category'],
                'assessment_proficiency': skill['proficiency'],
                'in_resume': in_resume,
                'status': status,
                'project_evidence': project_evidence
            })

        cursor.close()
        return render_template(
            'profile.html',
            student=student,
            resume=resume,
            resume_matches=resume_matches,
            resume_comparison=resume_comparison,
            projects=projects
        )
    finally:
        conn.close()

@student_bp.route('/portfolio/project', methods=['POST'])
@login_required
def add_project():
    title = request.form.get('title', '').strip()
    github_url = request.form.get('github_url', '').strip()
    technologies = request.form.get('technologies', '').strip()
    description = request.form.get('description', '').strip()

    if not title or not technologies or not description:
        flash('Project title, technologies, and description are required.', 'warning')
        return redirect(url_for('student.profile') + '#project-portfolio')
    if not is_valid_github_url(github_url):
        flash('Enter a valid GitHub repository URL.', 'warning')
        return redirect(url_for('student.profile') + '#project-portfolio')

    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('student.profile') + '#project-portfolio')
    try:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO student_projects (student_id, title, github_url, technologies, description)
            VALUES (%s, %s, %s, %s, %s)
        """, (session['user_id'], title, github_url or None, technologies, description))
        conn.commit()
        cursor.close()
        flash('Project added to your portfolio.', 'success')
    except Exception as e:
        print(f"[Add Project Error]: {e}")
        flash('Could not add the project.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('student.profile') + '#project-portfolio')

@student_bp.route('/portfolio/project/<int:project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('student.profile') + '#project-portfolio')
    try:
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM student_projects WHERE id = %s AND student_id = %s",
            (project_id, session['user_id'])
        )
        conn.commit()
        cursor.close()
        flash('Project removed from your portfolio.', 'success')
    except Exception as e:
        print(f"[Delete Project Error]: {e}")
        flash('Could not remove the project.', 'danger')
    finally:
        conn.close()
    return redirect(url_for('student.profile') + '#project-portfolio')

@student_bp.route('/resume/upload', methods=['POST'])
@login_required
def upload_resume():
    resume = request.files.get('resume')
    if resume is None or not resume.filename:
        flash('Choose a PDF resume to upload.', 'warning')
        return redirect(url_for('student.profile') + '#resume-skills')

    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('student.profile') + '#resume-skills')

    try:
        _, skills, _ = fetch_student_context(conn, session['user_id'])
        filename, extracted_text = extract_resume_text(
            resume,
            current_app.config.get('MAX_RESUME_SIZE', 5 * 1024 * 1024)
        )
        matches = extract_skill_matches(extracted_text, skills)

        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO student_resume_extractions
            (student_id, original_filename, extracted_text, extracted_skills)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                original_filename = VALUES(original_filename),
                extracted_text = VALUES(extracted_text),
                extracted_skills = VALUES(extracted_skills),
                uploaded_at = CURRENT_TIMESTAMP
        """, (
            session['user_id'],
            filename,
            extracted_text,
            json.dumps(matches)
        ))
        conn.commit()
        cursor.close()

        flash(
            'Resume processed successfully. {} technical skill{} detected.'.format(
                len(matches), '' if len(matches) == 1 else 's'
            ),
            'success'
        )
    except ResumeExtractionError as error:
        flash(str(error), 'danger')
    except Exception as error:
        current_app.logger.exception('Resume upload failed for student_id=%s', session['user_id'])
        flash('The resume could not be processed. Please try again.', 'danger')
    finally:
        conn.close()

    return redirect(url_for('student.profile') + '#resume-skills')

def _load_question_bank(cursor, skill_id, level):
    cursor.execute(
        "SELECT model_id, questions FROM question_banks WHERE skill_id = %s AND proficiency_level = %s",
        (skill_id, level)
    )
    row = cursor.fetchone()
    if not row or row['model_id'] != FIXED_QUESTION_BANK_VERSION:
        return None

    questions = row['questions']
    if isinstance(questions, str):
        try:
            questions = json.loads(questions)
        except json.JSONDecodeError as error:
            raise QuestionBankError('The cached question bank is invalid.') from error
    return validate_questions({'questions': questions}, QUESTIONS_PER_LEVEL)


def _get_or_generate_question_bank(conn, cursor, skill, level):
    questions = _load_question_bank(cursor, skill['id'], level)
    if questions is not None:
        return questions

    questions = get_fixed_questions(skill['name'], level, QUESTIONS_PER_LEVEL)
    cursor.execute("""
        INSERT INTO question_banks (skill_id, proficiency_level, model_id, questions)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            model_id = VALUES(model_id),
            questions = VALUES(questions),
            generated_at = CURRENT_TIMESTAMP
    """, (
        skill['id'], level, FIXED_QUESTION_BANK_VERSION, json.dumps(questions)
    ))
    conn.commit()
    cached = _load_question_bank(cursor, skill['id'], level)
    if cached is None:
        raise QuestionBankError('The fixed question bank could not be cached.')
    return cached


@student_bp.route('/assessment')
@login_required
def assessment():
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('student.dashboard'))

    try:
        _, skills, _ = fetch_student_context(conn, session['user_id'])
        for skill in skills:
            skill['level_name'] = SKILL_LEVELS.get(skill['proficiency'], 'Not assessed')
            skill['completed'] = skill['proficiency'] >= len(SKILL_LEVELS)
            skill['next_level_name'] = SKILL_LEVELS.get(skill['proficiency'] + 1)
            skill['progress_percent'] = skill['proficiency'] * 100 // len(SKILL_LEVELS)
        return render_template(
            'assessment.html',
            skills=skills,
            total_levels=len(SKILL_LEVELS)
        )
    finally:
        conn.close()


@student_bp.route('/progress')
@login_required
def skill_progress():
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('student.dashboard'))

    cursor = None
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT id, name, category
            FROM skills
            ORDER BY id ASC
        """)
        skills = cursor.fetchall()

        cursor.execute("""
            SELECT id, taken_at, raw_snapshot
            FROM assessments
            WHERE student_id = %s
            ORDER BY taken_at ASC, id ASC
        """, (session['user_id'],))
        assessments = cursor.fetchall()

        progress_error = None
        legacy_assessment_count = 0
        try:
            progress, legacy_assessment_count = build_skill_progress(skills, assessments)
        except ValueError as error:
            current_app.logger.error(
                'Assessment history is invalid for student_id=%s: %s',
                session['user_id'], error
            )
            progress_error = 'Assessment history could not be compared because a saved result is invalid.'
            progress = None

        return render_template(
            'skill_progress.html',
            progress=progress,
            progress_error=progress_error,
            legacy_assessment_count=legacy_assessment_count
        )
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()


@student_bp.route('/assessment/<int:skill_id>', methods=['GET', 'POST'])
@login_required
def skill_assessment(skill_id):
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('student.dashboard'))

    cursor = None
    try:
        _, skills, careers = fetch_student_context(conn, session['user_id'])
        skill = next((item for item in skills if item['id'] == skill_id), None)
        if skill is None:
            abort(404)

        highest_level = skill['proficiency']
        if highest_level >= len(SKILL_LEVELS):
            return render_template(
                'skill_quiz.html',
                skill=skill,
                completed=True,
                questions=[],
                level=None,
                level_name=None
            )

        level = highest_level + 1
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            if request.form.get('level', type=int) != level:
                flash('Your quiz level changed. Please continue from the current level.', 'warning')
                return redirect(url_for('student.skill_assessment', skill_id=skill_id))

            try:
                questions = _load_question_bank(cursor, skill_id, level)
            except QuestionBankError as error:
                current_app.logger.error(
                    'Cached question bank is invalid for skill_id=%s level=%s: %s',
                    skill_id, level, error
                )
                flash('The cached question set is invalid. Please contact an administrator.', 'danger')
                return redirect(url_for('student.assessment'))
            if questions is None:
                flash('This question set is not ready. Open the skill again to generate it.', 'warning')
                return redirect(url_for('student.skill_assessment', skill_id=skill_id))

            selected_answers = []
            for index in range(len(questions)):
                raw_answer = request.form.get('answer_{}'.format(index))
                try:
                    answer = int(raw_answer)
                except (TypeError, ValueError):
                    flash('Answer every question before submitting.', 'warning')
                    return redirect(url_for('student.skill_assessment', skill_id=skill_id))
                if answer not in range(4):
                    flash('One or more submitted answers are invalid.', 'warning')
                    return redirect(url_for('student.skill_assessment', skill_id=skill_id))
                selected_answers.append(answer)

            correct_count, required_correct, passed = score_answers(questions, selected_answers)
            new_highest_level = level if passed else highest_level

            cursor.execute("""
                INSERT INTO student_skill_progress (student_id, skill_id, highest_level_passed)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE highest_level_passed =
                    GREATEST(student_skill_progress.highest_level_passed, VALUES(highest_level_passed))
            """, (session['user_id'], skill_id, new_highest_level))
            cursor.execute("""
                INSERT INTO student_skills (student_id, skill_id, proficiency)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE proficiency = VALUES(proficiency)
            """, (session['user_id'], skill_id, new_highest_level))

            snapshot = {
                'skill_id': skill_id,
                'skill_name': skill['name'],
                'level': level,
                'correct': correct_count,
                'total': len(questions),
                'passed': passed
            }
            cursor.execute("""
                INSERT INTO assessments (student_id, average_score, raw_snapshot)
                VALUES (%s, %s, %s)
            """, (
                session['user_id'],
                round(correct_count * 5 / len(questions), 2),
                json.dumps(snapshot)
            ))

            skill['proficiency'] = new_highest_level
            skill_map = {item['id']: item['proficiency'] for item in skills}
            portfolio_skill_names = fetch_portfolio_skill_names(conn, session['user_id'])
            analysis = compute_career_analysis(skill_map, careers, portfolio_skill_names)
            cursor.execute("DELETE FROM recommendations WHERE student_id = %s", (session['user_id'],))
            for item in analysis:
                cursor.execute("""
                    INSERT INTO recommendations (student_id, career_id, match_percentage)
                    VALUES (%s, %s, %s)
                """, (session['user_id'], item['career_id'], item['match_percentage']))

                for breakdown in item['breakdown']:
                    if breakdown['gap'] > 0:
                        priority, topics, resources = get_curriculum_details(
                            breakdown['skill_name'], breakdown['gap']
                        )
                        cursor.execute("""
                            INSERT INTO learning_roadmaps
                            (student_id, career_id, skill_id, current_proficiency, target_proficiency,
                             priority, suggested_topics, learning_resources)
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                                current_proficiency = VALUES(current_proficiency),
                                target_proficiency = VALUES(target_proficiency),
                                priority = VALUES(priority)
                        """, (
                            session['user_id'], item['career_id'], breakdown['skill_id'],
                            breakdown['current_proficiency'], breakdown['required_proficiency'],
                            priority, topics, resources
                        ))
                    else:
                        cursor.execute("""
                            DELETE FROM learning_roadmaps
                            WHERE student_id = %s AND career_id = %s AND skill_id = %s
                        """, (session['user_id'], item['career_id'], breakdown['skill_id']))

            conn.commit()
            if passed:
                flash(
                    '{} passed: {} correct. Next: {}.'.format(
                        skill['name'], correct_count,
                        SKILL_LEVELS.get(new_highest_level + 1, 'assessment complete')
                    ),
                    'success'
                )
            else:
                flash(
                    '{} correct; {} needed to pass {}. Retry this level.'.format(
                        correct_count, required_correct, SKILL_LEVELS[level]
                    ),
                    'warning'
                )
            return redirect(url_for('student.skill_assessment', skill_id=skill_id))

        try:
            question_bank = _get_or_generate_question_bank(conn, cursor, skill, level)
        except QuestionBankError as error:
            current_app.logger.error(
                'Fixed question bank failed for skill_id=%s level=%s: %s',
                skill_id, level, error
            )
            flash(str(error), 'danger')
            return redirect(url_for('student.assessment'))

        questions = [
            {'question': item['question'], 'choices': item['choices']}
            for item in question_bank
        ]
        return render_template(
            'skill_quiz.html',
            skill=skill,
            completed=False,
            questions=questions,
            level=level,
            level_name=SKILL_LEVELS[level],
            passing_score=(QUESTIONS_PER_LEVEL * 2 + 2) // 3
        )
    finally:
        if cursor is not None:
            cursor.close()
        conn.close()

@student_bp.route('/analysis')
@login_required
def analysis():
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('student.dashboard'))

    try:
        _, skills, careers = fetch_student_context(conn, session['user_id'])
        skill_map = {s['id']: s['proficiency'] for s in skills}
        skill_priorities = compute_skill_priority_ranking(skill_map, careers)
        has_assessment = any(skill['proficiency'] > 0 for skill in skills)

        if not has_assessment:
            return render_template(
                'analysis.html',
                has_assessment=False,
                analysis=[],
                selected_career=None,
                skill_priorities=skill_priorities
            )

        portfolio_skill_names = fetch_portfolio_skill_names(conn, session['user_id'])
        analysis_results = compute_career_analysis(skill_map, careers, portfolio_skill_names)

        selected_id = request.args.get('career_id', type=int)
        selected_career = next((c for c in analysis_results if c['career_id'] == selected_id), analysis_results[0])

        return render_template(
            'analysis.html',
            has_assessment=True,
            analysis=analysis_results,
            selected_career=selected_career,
            skill_priorities=skill_priorities
        )
    finally:
        conn.close()

@student_bp.route('/roadmap', methods=['GET', 'POST'])
@login_required
def roadmap():
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('student.dashboard'))

    try:
        _, skills, careers = fetch_student_context(conn, session['user_id'])
        skill_map = {s['id']: s['proficiency'] for s in skills}
        portfolio_skill_names = fetch_portfolio_skill_names(conn, session['user_id'])
        analysis_results = compute_career_analysis(skill_map, careers, portfolio_skill_names)

        selected_career_id = request.args.get('career_id', type=int)
        if not selected_career_id and analysis_results:
            selected_career_id = analysis_results[0]['career_id']

        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT lr.*, s.name AS skill_name, c.title AS career_title
            FROM learning_roadmaps lr
            JOIN skills s ON lr.skill_id = s.id
            JOIN careers c ON lr.career_id = c.id
            WHERE lr.student_id = %s AND lr.career_id = %s
            ORDER BY FIELD(lr.priority, 'High', 'Medium', 'Low'), lr.skill_id ASC
        """, (session['user_id'], selected_career_id))
        roadmap_items = cursor.fetchall()
        cursor.close()

        return render_template(
            'roadmap.html',
            careers=analysis_results,
            selected_career_id=selected_career_id,
            roadmap_items=roadmap_items
        )
    finally:
        conn.close()

@student_bp.route('/roadmap/update-status', methods=['POST'])
@login_required
def update_roadmap_status():
    data = request.get_json()
    roadmap_id = data.get('roadmap_id')
    new_status = data.get('status')

    if new_status not in ['Not Started', 'In Progress', 'Completed']:
        return jsonify({'success': False, 'message': 'Invalid status value'}), 400

    conn = get_db_connection()
    if not conn:
        return jsonify({'success': False, 'message': 'Database error'}), 500

    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE learning_roadmaps
            SET status = %s
            WHERE id = %s AND student_id = %s
        """, (new_status, roadmap_id, session['user_id']))
        conn.commit()
        cursor.close()
        return jsonify({'success': True})
    finally:
        conn.close()

@student_bp.route('/report/download')
@login_required
def download_report():
    conn = get_db_connection()
    if not conn:
        flash('Database connection error.', 'danger')
        return redirect(url_for('student.dashboard'))

    try:
        student, skills, careers = fetch_student_context(conn, session['user_id'])
        skill_map = {s['id']: s['proficiency'] for s in skills}
        portfolio_skill_names = fetch_portfolio_skill_names(conn, session['user_id'])
        analysis_results = compute_career_analysis(skill_map, careers, portfolio_skill_names)
        top_career = analysis_results[0] if analysis_results else None

        roadmap_items = []
        if top_career:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT lr.*, s.name AS skill_name
                FROM learning_roadmaps lr
                JOIN skills s ON lr.skill_id = s.id
                WHERE lr.student_id = %s AND lr.career_id = %s
                ORDER BY FIELD(lr.priority, 'High', 'Medium', 'Low')
            """, (session['user_id'], top_career['career_id']))
            roadmap_items = cursor.fetchall()
            cursor.close()

        pdf_buffer = generate_student_report_pdf(student, skills, top_career, roadmap_items)
        filename = f"Skill_Gap_Report_{student['student_code']}.pdf"
        return send_file(pdf_buffer, as_attachment=True, download_name=filename, mimetype='application/pdf')
    finally:
        conn.close()