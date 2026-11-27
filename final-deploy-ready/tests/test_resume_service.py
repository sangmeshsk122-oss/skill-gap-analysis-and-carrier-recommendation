import io
import unittest

from werkzeug.datastructures import FileStorage

from services.resume_service import extract_skill_matches, extract_resume_text, ResumeExtractionError


class ResumeServiceTests(unittest.TestCase):
    def test_extract_skill_matches_uses_skill_aliases(self):
        skills = [
            {'id': 1, 'name': 'Python', 'category': 'Programming'},
            {'id': 7, 'name': 'SQL', 'category': 'Database'},
            {'id': 11, 'name': 'Machine Learning', 'category': 'Data & AI'},
            {'id': 3, 'name': 'C', 'category': 'Systems'},
        ]

        matches = extract_skill_matches(
            'Built Python APIs with PostgreSQL, TensorFlow, and C++ services.',
            skills
        )

        self.assertEqual(
            {item['skill_name'] for item in matches},
            {'Python', 'SQL', 'Machine Learning', 'C'}
        )

    def test_rejects_non_pdf_file(self):
        upload = FileStorage(
            stream=io.BytesIO(b'not a pdf'),
            filename='resume.txt'
        )

        with self.assertRaises(ResumeExtractionError):
            extract_resume_text(upload, 5 * 1024 * 1024)


if __name__ == '__main__':
    unittest.main()
