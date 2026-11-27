import unittest

from services.fixed_question_bank import SKILL_CONCEPTS
from services.question_service import (
    QuestionBankError,
    get_fixed_questions,
    score_answers,
    validate_questions
)


class QuestionServiceTests(unittest.TestCase):
    def test_fixed_bank_has_twenty_questions_for_every_skill_and_level(self):
        question_count = 0

        self.assertEqual(len(SKILL_CONCEPTS), 11)
        for skill_name in SKILL_CONCEPTS:
            skill_questions = []
            for level in range(1, 6):
                questions = get_fixed_questions(skill_name, level, 20)
                self.assertEqual(len(questions), 20)
                self.assertEqual(len({item['question'] for item in questions}), 20)
                skill_questions.extend(item['question'] for item in questions)
                question_count += len(questions)
            self.assertEqual(len(set(skill_questions)), 100)

        self.assertEqual(question_count, 1100)

    def test_fixed_question_choices_and_answers_validate(self):
        for skill_name in SKILL_CONCEPTS:
            for level in range(1, 6):
                questions = get_fixed_questions(skill_name, level, 20)
                self.assertEqual(validate_questions({'questions': questions}, 20), questions)

    def test_unknown_skill_has_an_explicit_error(self):
        with self.assertRaises(QuestionBankError):
            get_fixed_questions('Unknown skill', 1, 20)

    def test_scoring_requires_two_thirds_to_pass(self):
        questions = get_fixed_questions('Python', 1, 20)
        passed = [
            item['correct_index'] if index < 14 else (item['correct_index'] + 1) % 4
            for index, item in enumerate(questions)
        ]
        failed = [
            item['correct_index'] if index < 13 else (item['correct_index'] + 1) % 4
            for index, item in enumerate(questions)
        ]

        self.assertEqual(score_answers(questions, passed), (14, 14, True))
        self.assertEqual(score_answers(questions, failed), (13, 14, False))


if __name__ == '__main__':
    unittest.main()
