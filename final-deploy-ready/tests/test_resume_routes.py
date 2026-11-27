import io
import os
import unittest
from unittest.mock import patch

from flask import Flask
from reportlab.pdfgen import canvas

from routes.student_routes import student_bp


class FakeCursor:
    def __init__(self):
        self.executions = []

    def execute(self, query, params=None):
        self.executions.append((query, params))

    def close(self):
        pass


class FakeConnection:
    def __init__(self):
        self.test_cursor = FakeCursor()
        self.committed = False
        self.closed = False

    def cursor(self, *args, **kwargs):
        return self.test_cursor

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def make_resume_pdf():
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, 'Python and SQL developer')
    pdf.save()
    buffer.seek(0)
    return buffer


class ResumeUploadRouteTests(unittest.TestCase):
    def setUp(self):
        template_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        self.app = Flask(__name__, template_folder=template_folder)
        self.app.config['SECRET_KEY'] = 'test-secret'
        self.app.register_blueprint(student_bp)

    def test_upload_saves_skills_and_returns_to_resume_section(self):
        connection = FakeConnection()
        skills = [
            {'id': 1, 'name': 'Python', 'category': 'Programming'},
            {'id': 7, 'name': 'SQL', 'category': 'Database'},
        ]

        with patch('routes.student_routes.get_db_connection', return_value=connection), \
                patch('routes.student_routes.fetch_student_context', return_value=(None, skills, [])):
            with self.app.test_client() as client:
                with client.session_transaction() as session:
                    session['user_id'] = 1
                    session['role'] = 'student'

                response = client.post(
                    '/student/resume/upload',
                    data={'resume': (make_resume_pdf(), 'resume.pdf')},
                    content_type='multipart/form-data'
                )

                with client.session_transaction() as session:
                    flashes = session.get('_flashes', [])

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/student/profile#resume-skills'))
        self.assertTrue(connection.committed)
        self.assertTrue(connection.closed)
        insert = next(
            (params for query, params in connection.test_cursor.executions
             if 'INSERT INTO student_resume_extractions' in query),
            None
        )
        self.assertIsNotNone(insert)
        self.assertIn('"skill_name": "Python"', insert[3])
        self.assertIn('Resume processed successfully. 2 technical skills detected.', flashes[-1][1])


if __name__ == '__main__':
    unittest.main()
