LEARNING_CURRICULUM = {
    'Python': {
        'topics': 'Data structures, OOP, decorators, file I/O, virtual environments, REST APIs',
        'resources': 'Official Python Docs, Real Python Tutorials, Automate the Boring Stuff'
    },
    'Java': {
        'topics': 'JVM internals, OOP principles, Collections Framework, Streams API, Spring Boot basics',
        'resources': 'Oracle Java Tutorials, Baeldung Guides, MOOC.fi Java Programming'
    },
    'C': {
        'topics': 'Pointers, manual memory allocation, structs, file descriptors, compiler toolchains',
        'resources': 'Beej’s Guide to C Programming, K&R The C Programming Language'
    },
    'HTML': {
        'topics': 'Semantic HTML5 tags, forms & validation, ARIA accessibility standards, SEO structure',
        'resources': 'MDN Web Docs (HTML), web.dev Learn HTML'
    },
    'CSS': {
        'topics': 'Box model, Flexbox, CSS Grid, responsive media queries, CSS custom properties',
        'resources': 'MDN Web Docs (CSS), CSS-Tricks Complete Guide to Grid & Flexbox'
    },
    'JavaScript': {
        'topics': 'ES6+ syntax, asynchronous JS (Promises/async-await), DOM APIs, Fetch API, closures',
        'resources': 'JavaScript.info, MDN Web Docs (JavaScript), Eloquent JavaScript'
    },
    'SQL': {
        'topics': 'Normalization (1NF-3NF), JOIN operations, indexing, transactions, aggregate queries',
        'resources': 'SQLBolt, PostgreSQL/MySQL Official Documentation, Mode SQL Tutorial'
    },
    'Communication': {
        'topics': 'Technical specification writing, code review etiquette, structured presentations',
        'resources': 'Google Technical Writing Courses, Toastmasters Competent Communication'
    },
    'Problem Solving': {
        'topics': 'Divide and conquer, edge-case analysis, systematic debugging, time-space trade-offs',
        'resources': 'How to Solve It (Polya), HackerRank Problem Solving Track'
    },
    'Data Structures': {
        'topics': 'Arrays, linked lists, stacks, queues, hash tables, binary trees, graph traversal (BFS/DFS)',
        'resources': 'Open Data Structures, GeeksforGeeks DSA Self-Paced, NeetCode Roadmap'
    },
    'Machine Learning': {
        'topics': 'Linear/logistic regression, decision trees, cross-validation, feature engineering, Scikit-Learn',
        'resources': 'Scikit-Learn User Guide, Andrew Ng Machine Learning Specialization, Kaggle Learn'
    }
}

PORTFOLIO_EVIDENCE_BONUS = 0.2


def compute_career_analysis(student_skills_map, careers_data, portfolio_skill_names=None):
    """
    Deterministic Weighted Compatibility Engine:
    - Skill Gap = max(0, Required Proficiency - Current Proficiency)
    - Weighted Skill Attainment = min(Current / Required + Portfolio Evidence Bonus, 1.0) * Weight
    - Match Percentage = (Sum of Weighted Skill Attainment / Sum of Weights) * 100

    A skill listed in at least one project receives a capped 0.2 normalized
    attainment bonus. Quiz proficiency, skill gaps, and status remain unchanged.
    """
    results = []
    portfolio_skill_names = {
        name.strip().casefold()
        for name in (portfolio_skill_names or set())
        if name.strip()
    }

    for career in careers_data:
        req_skills = career['required_skills']
        if not req_skills:
            continue

        total_weight = 0.0
        earned_weight = 0.0
        skill_breakdown = []
        strong_skills = []
        weak_skills = []
        missing_skills = []

        for req in req_skills:
            skill_id = req['skill_id']
            skill_name = req['skill_name']
            req_level = req['required_proficiency']
            weight = float(req['weight'])
            curr_level = student_skills_map.get(skill_id, 0)

            gap = max(0, req_level - curr_level)
            quiz_attainment = min(curr_level / req_level, 1.0) if req_level > 0 else 1.0
            has_portfolio_evidence = skill_name.casefold() in portfolio_skill_names
            portfolio_bonus = PORTFOLIO_EVIDENCE_BONUS if has_portfolio_evidence else 0.0
            attainment_ratio = min(quiz_attainment + portfolio_bonus, 1.0)

            total_weight += weight
            earned_weight += attainment_ratio * weight

            if curr_level == 0:
                status = 'Missing'
                missing_skills.append(skill_name)
            elif gap > 0:
                status = 'Needs Improvement'
                weak_skills.append(skill_name)
            else:
                status = 'Proficient'
                strong_skills.append(skill_name)

            skill_breakdown.append({
                'skill_id': skill_id,
                'skill_name': skill_name,
                'current_proficiency': curr_level,
                'required_proficiency': req_level,
                'gap': gap,
                'weight': weight,
                'status': status,
                'portfolio_evidence': has_portfolio_evidence
            })

        match_percentage = round((earned_weight / total_weight) * 100, 2) if total_weight > 0 else 0.0

        results.append({
            'career_id': career['id'],
            'career_title': career['title'],
            'description': career['description'],
            'industry_outlook': career['industry_outlook'],
            'match_percentage': match_percentage,
            'strong_skills': strong_skills,
            'weak_skills': weak_skills,
            'missing_skills': missing_skills,
            'breakdown': skill_breakdown
        })

    results.sort(key=lambda x: x['match_percentage'], reverse=True)
    return results


def compute_skill_priority_ranking(student_skills_map, careers_data):
    """Rank missing skills by accumulated gap times career importance weight."""
    priorities = {}

    for career in careers_data:
        for req in career['required_skills']:
            skill_id = req['skill_id']
            skill_name = req['skill_name']
            required_level = req['required_proficiency']
            current_level = student_skills_map.get(skill_id, 0)
            gap = max(0, required_level - current_level)
            if gap == 0:
                continue

            priority = priorities.setdefault(skill_id, {
                'skill_id': skill_id,
                'skill_name': skill_name,
                'current_proficiency': current_level,
                'priority_score': 0.0,
                'affected_careers': []
            })
            priority['priority_score'] += gap * float(req['weight'])
            priority['affected_careers'].append({
                'career_title': career['title'],
                'gap': gap
            })

    results = list(priorities.values())
    for item in results:
        item['priority_score'] = round(item['priority_score'], 2)
    results.sort(
        key=lambda item: (
            -item['priority_score'],
            -len(item['affected_careers']),
            item['skill_name'].casefold()
        )
    )
    return results


def get_curriculum_details(skill_name, gap):
    priority = 'High' if gap >= 3 else ('Medium' if gap == 2 else 'Low')
    default_info = {
        'topics': f'Core fundamentals, applied syntax, and practical project implementation in {skill_name}.',
        'resources': f'Official {skill_name} Documentation, Standard Reference Textbooks, Hands-on Labs'
    }
    info = LEARNING_CURRICULUM.get(skill_name, default_info)
    return priority, info['topics'], info['resources']