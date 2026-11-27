import json
import os
import unittest
from unittest.mock import patch

from flask import Flask

from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from services.question_service import FIXED_QUESTION_BANK_VERSION


def question_bank():
    return [
        {
            'question': 'Question {}'.format(index),
            'choices': ['A', 'B', 'C', 'D'],
            'correct_index': 0,
            'explanation': 'A is correct.'
        }
        for index in range(20)
    ]


class FakeCursor:
    def __init__(self):
        self.executions = []
        self.row = None

    def execute(self, query, params=None):
        self.executions.append((query, params))
        if 'FROM question_banks' in query:
            self.row = {
                'model_id': FIXED_QUESTION_BANK_VERSION,
                'questions': json.dumps(question_bank())
            }

    def fetchone(self):
        return self.row

    def fetchall(self):
        return []

    def close(self):
        pass


class FakeConnection:
    def __init__(self):
        self.test_cursor = FakeCursor()
        self.committed = False
        self.closed = False

    def cursor(self, dictionary=False):
        return self.test_cursor

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class StudentQuizRouteTests(unittest.TestCase):
    def setUp(self):
        template_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        self.app = Flask(__name__, template_folder=template_folder)
        self.app.config['SECRET_KEY'] = 'test-secret'
        self.app.register_blueprint(auth_bp)
        self.app.register_blueprint(student_bp)

    def submit_quiz(self, correct_answers):
        connection = FakeConnection()
        skill = {
            'id': 1,
            'name': 'Python',
            'description': 'Programming',
            'category': 'Programming',
            'proficiency': 0
        }
        answers = {
            'level': '1',
            **{
                'answer_{}'.format(index): str(0 if index < correct_answers else 1)
                for index in range(20)
            }
        }

        with patch('routes.student_routes.get_db_connection', return_value=connection), \
                patch('routes.student_routes.fetch_student_context', return_value=(None, [skill], [])), \
                patch('routes.student_routes.compute_career_analysis', return_value=[]):
            with self.app.test_client() as client:
                with client.session_transaction() as session:
                    session['user_id'] = 1
                    session['role'] = 'student'
                response = client.post('/student/assessment/1', data=answers)

        return response, connection

    def test_passing_quiz_saves_verified_progress(self):
        response, connection = self.submit_quiz(14)

        progress_write = next(
            (params for query, params in connection.test_cursor.executions
             if 'INSERT INTO student_skill_progress' in query),
            None
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(progress_write, (1, 1, 1))
        self.assertTrue(connection.committed)
        self.assertTrue(connection.closed)

    def test_failing_quiz_keeps_current_level_locked(self):
        response, connection = self.submit_quiz(13)

        progress_write = next(
            (params for query, params in connection.test_cursor.executions
             if 'INSERT INTO student_skill_progress' in query),
            None
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(progress_write, (1, 1, 0))
        self.assertTrue(connection.committed)

    def test_quiz_page_renders_questions_without_answer_keys(self):
        connection = FakeConnection()
        skill = {
            'id': 1,
            'name': 'Python',
            'description': 'Programming',
            'category': 'Programming',
            'proficiency': 0
        }

        with patch('routes.student_routes.get_db_connection', return_value=connection), \
                patch('routes.student_routes.fetch_student_context', return_value=(None, [skill], [])), \
                patch(
                    'routes.student_routes._get_or_generate_question_bank',
                    return_value=question_bank()
                ):
            with self.app.test_client() as client:
                with client.session_transaction() as session:
                    session['user_id'] = 1
                    session['role'] = 'student'
                response = client.get('/student/assessment/1')

        page = response.get_data(as_text=True)
        input_names = {
            'answer_{}'.format(index)
            for index in range(20)
        }
        rendered_names = {
            name for name in input_names
            if 'name="{}"'.format(name) in page
        }
        self.assertEqual(response.status_code, 200)
        self.assertEqual(rendered_names, input_names)
        self.assertNotIn('correct_index', page)
        self.assertNotIn('A is correct.', page)


if __name__ == '__main__':
    unittest.main()
