import json


def build_skill_progress(skills, assessments):
    skill_ids = {skill['id'] for skill in skills}
    skill_names = {skill['name'] for skill in skills}
    attempts_by_skill = {skill_id: [] for skill_id in skill_ids}
    legacy_assessment_count = 0

    for assessment in assessments:
        snapshot = assessment['raw_snapshot']
        if isinstance(snapshot, str):
            try:
                snapshot = json.loads(snapshot)
            except json.JSONDecodeError as error:
                raise ValueError('An assessment contains invalid JSON data.') from error
        if not isinstance(snapshot, dict):
            raise ValueError('An assessment snapshot must be an object.')

        if 'skill_id' not in snapshot:
            is_legacy_summary = (
                bool(snapshot)
                and set(snapshot).issubset(skill_names)
                and all(
                    isinstance(value, (int, float))
                    and not isinstance(value, bool)
                    and 0 <= value <= 5
                    for value in snapshot.values()
                )
            )
            if is_legacy_summary:
                legacy_assessment_count += 1
                continue
            raise ValueError('An assessment snapshot is missing required quiz results.')

        try:
            skill_id = int(snapshot['skill_id'])
            level = int(snapshot['level'])
            correct = int(snapshot['correct'])
            total = int(snapshot['total'])
            passed = snapshot['passed']
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError('An assessment snapshot is missing required quiz results.') from error

        if skill_id not in skill_ids:
            continue
        if level not in range(1, 6) or total <= 0 or correct not in range(total + 1):
            raise ValueError('An assessment snapshot contains invalid quiz results.')
        if not isinstance(passed, bool):
            raise ValueError('An assessment pass result must be true or false.')

        attempts_by_skill[skill_id].append({
            'assessment_id': assessment['id'],
            'taken_at': assessment['taken_at'],
            'level': level,
            'correct': correct,
            'total': total,
            'score_percent': round(correct * 100 / total),
            'passed': passed,
        })

    progress = []
    for skill in skills:
        attempts = attempts_by_skill[skill['id']]
        verified_level = 0
        for attempt in attempts:
            if attempt['passed']:
                verified_level = max(verified_level, attempt['level'])
            attempt['verified_level'] = verified_level

        previous = attempts[-2] if len(attempts) >= 2 else None
        current = attempts[-1] if attempts else None
        progress.append({
            'skill_name': skill['name'],
            'category': skill['category'],
            'attempt_count': len(attempts),
            'previous': previous,
            'current': current,
            'proficiency_change': (
                current['verified_level'] - previous['verified_level']
                if previous and current else None
            ),
            'score_change': (
                current['score_percent'] - previous['score_percent']
                if previous and current else None
            ),
            'verified_level': verified_level,
        })

    return progress, legacy_assessment_count
