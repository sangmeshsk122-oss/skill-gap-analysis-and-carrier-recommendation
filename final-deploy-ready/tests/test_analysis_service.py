import unittest

from services.analysis_service import (
    compute_career_analysis,
    compute_skill_priority_ranking
)


class CareerAnalysisPortfolioEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.careers = [{
            'id': 1,
            'title': 'Backend Developer',
            'description': 'Builds backend services.',
            'industry_outlook': 'Strong',
            'required_skills': [{
                'skill_id': 1,
                'skill_name': 'Python',
                'required_proficiency': 4,
                'weight': 1.0,
            }],
        }]

    def test_project_skill_adds_match_score_without_changing_quiz_gap(self):
        without_evidence = compute_career_analysis({1: 2}, self.careers)[0]
        with_evidence = compute_career_analysis(
            {1: 2}, self.careers, {'python'}
        )[0]

        self.assertEqual(without_evidence['match_percentage'], 50.0)
        self.assertEqual(with_evidence['match_percentage'], 70.0)
        self.assertEqual(with_evidence['breakdown'][0]['current_proficiency'], 2)
        self.assertEqual(with_evidence['breakdown'][0]['gap'], 2)
        self.assertEqual(with_evidence['breakdown'][0]['status'], 'Needs Improvement')
        self.assertTrue(with_evidence['breakdown'][0]['portfolio_evidence'])

    def test_portfolio_bonus_is_capped_at_full_attainment(self):
        result = compute_career_analysis(
            {1: 4}, self.careers, {'PYTHON'}
        )[0]

        self.assertEqual(result['match_percentage'], 100.0)
        self.assertEqual(result['breakdown'][0]['gap'], 0)
        self.assertTrue(result['breakdown'][0]['portfolio_evidence'])

    def test_unrelated_portfolio_skill_does_not_change_score(self):
        result = compute_career_analysis(
            {1: 2}, self.careers, {'javascript'}
        )[0]

        self.assertEqual(result['match_percentage'], 50.0)
        self.assertFalse(result['breakdown'][0]['portfolio_evidence'])

    def test_priority_ranking_aggregates_weighted_gaps_across_careers(self):
        careers = [
            {
                'title': 'Backend Developer',
                'required_skills': [
                    {'skill_id': 1, 'skill_name': 'Python', 'required_proficiency': 4, 'weight': 1.5},
                    {'skill_id': 2, 'skill_name': 'SQL', 'required_proficiency': 3, 'weight': 1.0},
                ],
            },
            {
                'title': 'Data Engineer',
                'required_skills': [
                    {'skill_id': 1, 'skill_name': 'Python', 'required_proficiency': 5, 'weight': 1.0},
                    {'skill_id': 2, 'skill_name': 'SQL', 'required_proficiency': 4, 'weight': 2.0},
                    {'skill_id': 3, 'skill_name': 'HTML', 'required_proficiency': 4, 'weight': 1.0},
                ],
            },
        ]

        priorities = compute_skill_priority_ranking(
            {1: 1, 2: 2, 3: 4}, careers
        )

        self.assertEqual(
            [(item['skill_name'], item['priority_score']) for item in priorities],
            [('Python', 8.5), ('SQL', 5.0)]
        )
        self.assertEqual(len(priorities[0]['affected_careers']), 2)
        self.assertEqual(priorities[0]['affected_careers'][0]['gap'], 3)


if __name__ == '__main__':
    unittest.main()
