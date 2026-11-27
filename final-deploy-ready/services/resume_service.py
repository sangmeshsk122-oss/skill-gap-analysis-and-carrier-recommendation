import io
import re

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from werkzeug.utils import secure_filename


class ResumeExtractionError(ValueError):
    pass


SKILL_ALIASES = {
    'Python': ('python',),
    'Java': ('java',),
    'C': ('c', 'c++'),
    'HTML': ('html', 'html5'),
    'CSS': ('css', 'css3'),
    'JavaScript': ('javascript', 'js', 'node.js', 'nodejs', 'typescript'),
    'SQL': ('sql', 'mysql', 'postgresql', 'postgres'),
    'Communication': ('communication', 'teamwork', 'stakeholder reporting', 'technical documentation'),
    'Problem Solving': ('problem solving', 'debugging', 'analytical thinking', 'algorithms'),
    'Data Structures': ('data structures', 'linked list', 'binary tree', 'graphs', 'hash map'),
    'Machine Learning': ('machine learning', 'machine-learning', 'deep learning', 'ml', 'tensorflow', 'pytorch'),
}


def extract_resume_text(file_storage, max_size):
    filename = secure_filename(file_storage.filename or '')
    if not filename.lower().endswith('.pdf'):
        raise ResumeExtractionError('Please upload a PDF resume.')

    data = file_storage.read(max_size + 1)
    if len(data) > max_size:
        raise ResumeExtractionError('The resume must be 5 MB or smaller.')
    if not data:
        raise ResumeExtractionError('The uploaded PDF is empty.')
    if b'%PDF-' not in data[:1024]:
        raise ResumeExtractionError('The uploaded file is not a valid PDF.')

    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        pages = [page.extract_text() or '' for page in reader.pages]
    except (PdfReadError, Exception) as error:
        raise ResumeExtractionError('The uploaded file could not be read as a PDF.') from error

    text = '\n'.join(pages).strip()
    if not text:
        raise ResumeExtractionError('No readable text was found in this PDF.')
    return filename, text


def extract_skill_matches(text, skills):
    normalized = re.sub(r'\s+', ' ', text).lower()
    matches = []

    for skill in skills:
        aliases = SKILL_ALIASES.get(skill['name'], (skill['name'],))
        detected = False
        for alias in aliases:
            if skill['name'] == 'C':
                pattern = r'(?<![A-Za-z0-9])c(?:\+\+)?(?![A-Za-z0-9])'
                if re.search(pattern, normalized, flags=re.IGNORECASE):
                    detected = True
                    break
            else:
                pattern = r'(?<![A-Za-z0-9])' + re.escape(alias.lower()) + r'(?![A-Za-z0-9])'
                if re.search(pattern, normalized):
                    detected = True
                    break
        if detected:
            matches.append({
                'skill_id': skill['id'],
                'skill_name': skill['name'],
                'category': skill['category'],
            })

    matches.sort(key=lambda item: item['skill_name'].lower())
    return matches
