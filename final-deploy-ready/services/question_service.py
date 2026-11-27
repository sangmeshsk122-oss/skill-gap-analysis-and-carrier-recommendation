from services.fixed_question_bank import SKILL_CONCEPTS

FIXED_QUESTION_BANK_VERSION = 'fixed-v1'


class QuestionBankError(Exception):
    pass


def score_answers(questions, selected_answers):
    if not questions or len(questions) != len(selected_answers):
        raise ValueError('Answers must be provided for every question.')
    if any(type(answer) is not int or answer not in range(4) for answer in selected_answers):
        raise ValueError('Submitted answers must be valid choice indexes.')

    correct_count = sum(
        answer == question['correct_index']
        for answer, question in zip(selected_answers, questions)
    )
    required_correct = (len(questions) * 2 + 2) // 3
    return correct_count, required_correct, correct_count >= required_correct


def validate_questions(payload, expected_count):
    if not isinstance(payload, dict) or not isinstance(payload.get('questions'), list):
        raise QuestionBankError('The question bank must contain a questions array.')

    questions = payload['questions']
    if len(questions) != expected_count:
        raise QuestionBankError(
            'The question bank contains {} questions; expected {}.'.format(len(questions), expected_count)
        )

    validated = []
    seen_questions = set()
    for index, question in enumerate(questions, start=1):
        if not isinstance(question, dict):
            raise QuestionBankError('Question {} is not a JSON object.'.format(index))

        prompt = question.get('question')
        choices = question.get('choices')
        correct_index = question.get('correct_index')
        explanation = question.get('explanation')

        if not isinstance(prompt, str) or not prompt.strip():
            raise QuestionBankError('Question {} has no question text.'.format(index))
        if prompt.strip().casefold() in seen_questions:
            raise QuestionBankError('The question bank contains duplicate questions.')
        if not isinstance(choices, list) or len(choices) != 4:
            raise QuestionBankError('Question {} must have exactly four choices.'.format(index))
        if any(not isinstance(choice, str) or not choice.strip() for choice in choices):
            raise QuestionBankError('Question {} has an empty choice.'.format(index))
        if len({choice.strip().casefold() for choice in choices}) != 4:
            raise QuestionBankError('Question {} has duplicate choices.'.format(index))
        if type(correct_index) is not int or correct_index not in range(4):
            raise QuestionBankError('Question {} has an invalid correct answer.'.format(index))
        if not isinstance(explanation, str) or not explanation.strip():
            raise QuestionBankError('Question {} has no answer explanation.'.format(index))

        seen_questions.add(prompt.strip().casefold())
        validated.append({
            'question': prompt.strip(),
            'choices': [choice.strip() for choice in choices],
            'correct_index': correct_index,
            'explanation': explanation.strip()
        })

    return validated


def get_fixed_questions(skill_name, level, expected_count):
    concepts = SKILL_CONCEPTS.get(skill_name)
    if concepts is None:
        raise QuestionBankError('No fixed questions are configured for {}.'.format(skill_name))
    if len(concepts) != expected_count:
        raise QuestionBankError(
            '{} has {} fixed questions; expected {}.'.format(
                skill_name, len(concepts), expected_count
            )
        )
    if type(level) is not int or level not in range(1, 6):
        raise QuestionBankError('The requested quiz level is invalid.')

    terms = [concept[0] for concept in concepts]
    definitions = [concept[1] for concept in concepts]
    questions = []

    for index, (term, definition, scenario) in enumerate(concepts):
        if level == 1:
            prompt = 'Which concept is described by: {}?'.format(definition)
            correct_answer = term
            choice_pool = terms
        elif level == 2:
            prompt = 'A practitioner encounters this situation: {}. Which concept applies?'.format(scenario)
            correct_answer = term
            choice_pool = terms
        elif level == 3:
            prompt = 'Which description best matches {}?'.format(term)
            correct_answer = definition
            choice_pool = definitions
        elif level == 4:
            prompt = 'A solution needs to address {}. Which concept should be considered first?'.format(scenario)
            correct_answer = term
            choice_pool = terms
        else:
            prompt = 'Which concept best supports this practice: {}; it is useful when {}?'.format(
                definition, scenario
            )
            correct_answer = term
            choice_pool = terms

        distractors = []
        for offset in range(1, len(choice_pool)):
            candidate = choice_pool[(index + offset) % len(choice_pool)]
            if candidate != correct_answer:
                distractors.append(candidate)
            if len(distractors) == 3:
                break

        correct_index = (index + level - 1) % 4
        choices = distractors
        choices.insert(correct_index, correct_answer)
        questions.append({
            'question': prompt,
            'choices': choices,
            'correct_index': correct_index,
            'explanation': '{}: {} Application: {}'.format(term, definition, scenario)
        })

    return validate_questions({'questions': questions}, expected_count)
