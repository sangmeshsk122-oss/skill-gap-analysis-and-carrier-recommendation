import os
import unittest
from unittest.mock import patch

from flask import Flask

from routes.student_routes import is_valid_github_url, student_bp


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


class ProjectRouteTests(unittest.TestCase):
    def setUp(self):
        template_folder = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
        self.app = Flask(__name__, template_folder=template_folder)
        self.app.config['SECRET_KEY'] = 'test-secret'
        self.app.register_blueprint(student_bp)

    def test_github_url_validation(self):
        self.assertTrue(is_valid_github_url('https://github.com/student/project'))
        self.assertTrue(is_valid_github_url(''))
        self.assertFalse(is_valid_github_url('https://example.com/project'))

    def test_add_project_saves_portfolio_entry(self):
        connection = FakeConnection()
        with patch('routes.student_routes.get_db_connection', return_value=connection):
            with self.app.test_client() as client:
                with client.session_transaction() as session:
                    session['user_id'] = 1
                    session['role'] = 'student'

                response = client.post('/student/portfolio/project', data={
                    'title': 'Inventory System',
                    'github_url': 'https://github.com/student/inventory',
                    'technologies': 'Python, SQL, Flask',
                    'description': 'A REST API for inventory management.'
                })

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.location.endswith('/student/profile#project-portfolio'))
        self.assertTrue(connection.committed)
        insert = next(
            (params for query, params in connection.test_cursor.executions
             if 'INSERT INTO student_projects' in query),
            None
        )
        self.assertEqual(insert, (
            1,
            'Inventory System',
            'https://github.com/student/inventory',
            'Python, SQL, Flask',
            'A REST API for inventory management.'
        ))

    def test_delete_project_is_scoped_to_student(self):
        connection = FakeConnection()
        with patch('routes.student_routes.get_db_connection', return_value=connection):
            with self.app.test_client() as client:
                with client.session_transaction() as session:
                    session['user_id'] = 7
                    session['role'] = 'student'

                response = client.post('/student/portfolio/project/12/delete')

        self.assertEqual(response.status_code, 302)
        self.assertTrue(connection.committed)
        delete = next(
            (params for query, params in connection.test_cursor.executions
             if 'DELETE FROM student_projects' in query),
            None
        )
        self.assertEqual(delete, (12, 7))


if __name__ == '__main__':
    unittest.main()
