import unittest
from datetime import datetime
import os
from unittest.mock import patch

from flask import Flask
from routes.auth_routes import auth_bp
from routes.student_routes import student_bp
from services.progress_service import build_skill_progress


class FakeCursor:
    def __init__(self):
        self.query = ''

    def execute(self, query, params=None):
        self.query = query

    def fetchall(self):
        if 'FROM skills' in self.query:
            return [
                {'id': 1, 'name': 'Python', 'category': 'Programming'},
                {'id': 2, 'name': 'SQL', 'category': 'Database'},
            ]
        return [
            {
                'id': 0,
                'taken_at': datetime(2025, 12, 31),
                'raw_snapshot': {'Python': 2, 'SQL': 1},
            },
            {
                'id': 1,
                'taken_at': datetime(2026, 1, 1),
                'raw_snapshot': {
                    'skill_id': 1, 'level': 1, 'correct': 12, 'total': 20, 'passed': False
                },
            },
            {
                'id': 2,
                'taken_at': datetime(2026, 1, 2),
                'raw_snapshot': {
                    'skill_id': 1, 'level': 1, 'correct': 16, 'total': 20, 'passed': True
                },
            },
        ]

    def close(self):
        pass


class FakeConnection:
    def __init__(self):
        self.test_cursor = FakeCursor()
        self.closed = False

    def cursor(self, dictionary=False):
        return self.test_cursor

    def close(self):
        self.closed = True


class SkillProgressServiceTests(unittest.TestCase):
    def setUp(self):
        self.skills = [
            {'id': 1, 'name': 'Python', 'category': 'Programming'},
            {'id': 2, 'name': 'SQL', 'category': 'Database'},
        ]

    def test_compares_latest_two_attempts_and_verified_level_gain(self):
        assessments = [
            {
                'id': 1,
                'taken_at': datetime(2026, 1, 1),
                'raw_snapshot': {
                    'skill_id': 1, 'level': 1, 'correct': 12, 'total': 20, 'passed': False
                },
            },
            {
                'id': 2,
                'taken_at': datetime(2026, 1, 2),
                'raw_snapshot': (
                    '{"skill_id": 1, "level": 1, "correct": 16, '
                    '"total": 20, "passed": true}'
                ),
            },
        ]

        progress, legacy_count = build_skill_progress(self.skills, assessments)

        self.assertEqual(progress[0]['previous']['score_percent'], 60)
        self.assertEqual(progress[0]['current']['score_percent'], 80)
        self.assertEqual(progress[0]['proficiency_change'], 1)
        self.assertEqual(progress[0]['score_change'], 20)
        self.assertEqual(progress[1]['attempt_count'], 0)
        self.assertIsNone(progress[1]['current'])
        self.assertEqual(legacy_count, 0)

    def test_first_assessment_has_no_previous_result_or_change(self):
        progress, legacy_count = build_skill_progress(
            self.skills,
            [{
                'id': 1,
                'taken_at': None,
                'raw_snapshot': {
                    'skill_id': 1, 'level': 1, 'correct': 15, 'total': 20, 'passed': True
                },
            }]
        )

        self.assertIsNone(progress[0]['previous'])
        self.assertIsNone(progress[0]['proficiency_change'])
        self.assertEqual(progress[0]['verified_level'], 1)
        self.assertEqual(legacy_count, 0)

    def test_ignores_legacy_summary_assessments(self):
        progress, legacy_count = build_skill_progress(
            self.skills,
            [{
                'id': 1,
                'taken_at': datetime(2026, 1, 1),
                'raw_snapshot': {'Python': 2, 'SQL': 1},
            }]
        )

        self.assertEqual(legacy_count, 1)
        self.assertEqual(progress[0]['attempt_count'], 0)
        self.assertEqual(progress[1]['attempt_count'], 0)

    def test_rejects_malformed_assessment_snapshot(self):
        with self.assertRaises(ValueError):
            build_skill_progress(self.skills, [{
                'id': 1,
                'taken_at': None,
                'raw_snapshot': {'skill_id': 1},
            }])

    def test_progress_page_renders_latest_attempt_comparison(self):
        template_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        app = Flask(__name__, template_folder=template_folder)
        app.config['SECRET_KEY'] = 'test-secret'
        app.register_blueprint(auth_bp)
        app.register_blueprint(student_bp)
        connection = FakeConnection()

        with patch('routes.student_routes.get_db_connection', return_value=connection):
            with app.test_client() as client:
                with client.session_transaction() as session:
                    session['user_id'] = 1
                    session['role'] = 'student'
                response = client.get('/student/progress')

        page = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Previous vs. Current Assessment', page)
        self.assertIn('Python', page)
        self.assertIn('+1 level', page)
        self.assertIn('Score +20 percentage points', page)
        self.assertIn('older summary assessment', page)
        self.assertTrue(connection.closed)


if __name__ == '__main__':
    unittest.main()
