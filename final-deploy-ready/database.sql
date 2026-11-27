CREATE DATABASE IF NOT EXISTS skill_gap_analysis;
USE skill_gap_analysis;

-- 1. Students & Administrators Table
CREATE TABLE IF NOT EXISTS students (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_code VARCHAR(30) UNIQUE NOT NULL,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(150) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    department VARCHAR(100) DEFAULT 'Computer Science',
    semester INT DEFAULT 1,
    education_details TEXT,
    career_interests VARCHAR(255),
    role ENUM('student', 'admin') DEFAULT 'student',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Master Skills Catalog
CREATE TABLE IF NOT EXISTS skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    category VARCHAR(80) NOT NULL,
    description TEXT
);

-- 3. Current Student Skill Proficiencies (Latest Snapshot)
CREATE TABLE IF NOT EXISTS student_skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    skill_id INT NOT NULL,
    proficiency INT NOT NULL CHECK (proficiency BETWEEN 0 AND 5),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_student_skill (student_id, skill_id),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
);

-- Quiz progress is separate from historical self-reported ratings.
CREATE TABLE IF NOT EXISTS student_skill_progress (
    student_id INT NOT NULL,
    skill_id INT NOT NULL,
    highest_level_passed INT NOT NULL DEFAULT 0 CHECK (highest_level_passed BETWEEN 0 AND 5),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id, skill_id),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
);

-- Fixed local question sets are cached and reused.
CREATE TABLE IF NOT EXISTS question_banks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    skill_id INT NOT NULL,
    proficiency_level INT NOT NULL CHECK (proficiency_level BETWEEN 1 AND 5),
    model_id VARCHAR(100) NOT NULL,
    questions JSON NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_skill_question_level (skill_id, proficiency_level),
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
);

-- 4. Historical Assessment Logs
CREATE TABLE IF NOT EXISTS assessments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    average_score DECIMAL(4,2) NOT NULL,
    raw_snapshot JSON NOT NULL,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- 5. Target Career Profiles
CREATE TABLE IF NOT EXISTS careers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(120) UNIQUE NOT NULL,
    description TEXT NOT NULL,
    industry_outlook VARCHAR(255)
);

-- 6. Career Required Skills & Weights
CREATE TABLE IF NOT EXISTS career_required_skills (
    id INT AUTO_INCREMENT PRIMARY KEY,
    career_id INT NOT NULL,
    skill_id INT NOT NULL,
    required_proficiency INT NOT NULL CHECK (required_proficiency BETWEEN 1 AND 5),
    weight DECIMAL(3,2) DEFAULT 1.00,
    UNIQUE KEY unique_career_skill (career_id, skill_id),
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
);

-- 7. Saved Career Recommendations
CREATE TABLE IF NOT EXISTS recommendations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    career_id INT NOT NULL,
    match_percentage DECIMAL(5,2) NOT NULL,
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE
);

-- 8. Personalized Learning Roadmaps
CREATE TABLE IF NOT EXISTS learning_roadmaps (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    career_id INT NOT NULL,
    skill_id INT NOT NULL,
    current_proficiency INT NOT NULL,
    target_proficiency INT NOT NULL,
    priority ENUM('High', 'Medium', 'Low') NOT NULL,
    suggested_topics TEXT NOT NULL,
    learning_resources TEXT NOT NULL,
    status ENUM('Not Started', 'In Progress', 'Completed') DEFAULT 'Not Started',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY unique_roadmap_item (student_id, career_id, skill_id),
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (career_id) REFERENCES careers(id) ON DELETE CASCADE,
    FOREIGN KEY (skill_id) REFERENCES skills(id) ON DELETE CASCADE
);

-- Latest extracted resume metadata for each student.
CREATE TABLE IF NOT EXISTS student_resume_extractions (
    student_id INT PRIMARY KEY,
    original_filename VARCHAR(255) NOT NULL,
    extracted_text MEDIUMTEXT,
    extracted_skills JSON NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- Student project portfolio and supporting skill evidence.
CREATE TABLE IF NOT EXISTS student_projects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    student_id INT NOT NULL,
    title VARCHAR(150) NOT NULL,
    github_url VARCHAR(500),
    technologies VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

-- Seed Required Skills
INSERT IGNORE INTO skills (id, name, category, description) VALUES
(1, 'Python', 'Programming', 'General-purpose programming, scripting, and backend development'),
(2, 'Java', 'Programming', 'Object-oriented enterprise application development'),
(3, 'C', 'Systems', 'Low-level memory management and procedural programming'),
(4, 'HTML', 'Web Frontend', 'Semantic document structure and web accessibility'),
(5, 'CSS', 'Web Frontend', 'Responsive layouts, Flexbox, Grid, and styling'),
(6, 'JavaScript', 'Web Frontend', 'Client-side interactivity, DOM manipulation, and ES6+'),
(7, 'SQL', 'Database', 'Relational database design, querying, and optimization'),
(8, 'Communication', 'Soft Skills', 'Technical documentation, stakeholder reporting, and teamwork'),
(9, 'Problem Solving', 'Core Engineering', 'Algorithmic thinking, debugging, and analytical decomposition'),
(10, 'Data Structures', 'Core Engineering', 'Arrays, trees, graphs, hash maps, and complexity analysis'),
(11, 'Machine Learning', 'Data & AI', 'Supervised/unsupervised algorithms, model evaluation, and pipelines');

-- Seed Target Careers
INSERT IGNORE INTO careers (id, title, description, industry_outlook) VALUES
(1, 'Software Developer', 'Designs, builds, tests, and maintains scalable software applications and backend services.', 'High demand across enterprise software, cloud platforms, and fintech.'),
(2, 'Data Analyst', 'Extracts, cleans, queries, and visualizes structured datasets to support business decisions.', 'Strong growth in healthcare, finance, e-commerce, and logistics.'),
(3, 'AI/ML Engineer', 'Develops, validates, and deploys statistical and machine learning models into production.', 'Rapid expansion in automation, predictive analytics, and NLP.'),
(4, 'Web Developer', 'Builds responsive, accessible full-stack web applications and RESTful interfaces.', 'Steady demand across digital agencies, SaaS companies, and startups.'),
(5, 'Cybersecurity Analyst', 'Monitors network infrastructure, assesses vulnerabilities, and secures system architectures.', 'Critical priority across government, banking, and cloud infrastructure.');

-- Seed Career Required Skills & Weights
-- 1. Software Developer
INSERT IGNORE INTO career_required_skills (career_id, skill_id, required_proficiency, weight) VALUES
(1, 1, 4, 1.30), (1, 2, 4, 1.20), (1, 3, 3, 0.90), (1, 7, 4, 1.10),
(1, 8, 3, 0.80), (1, 9, 5, 1.50), (1, 10, 5, 1.50);

-- 2. Data Analyst
INSERT IGNORE INTO career_required_skills (career_id, skill_id, required_proficiency, weight) VALUES
(2, 1, 4, 1.40), (2, 7, 5, 1.60), (2, 8, 4, 1.20), (2, 9, 4, 1.20), (2, 11, 3, 1.00);

-- 3. AI/ML Engineer
INSERT IGNORE INTO career_required_skills (career_id, skill_id, required_proficiency, weight) VALUES
(3, 1, 5, 1.60), (3, 7, 4, 1.00), (3, 9, 5, 1.40), (3, 10, 4, 1.30), (3, 11, 5, 1.80);

-- 4. Web Developer
INSERT IGNORE INTO career_required_skills (career_id, skill_id, required_proficiency, weight) VALUES
(4, 4, 5, 1.40), (4, 5, 5, 1.40), (4, 6, 5, 1.60), (4, 7, 3, 1.00), (4, 8, 3, 0.80), (4, 9, 4, 1.10);

-- 5. Cybersecurity Analyst
INSERT IGNORE INTO career_required_skills (career_id, skill_id, required_proficiency, weight) VALUES
(5, 1, 4, 1.30), (5, 3, 4, 1.40), (5, 7, 4, 1.20), (5, 8, 4, 1.10), (5, 9, 5, 1.50);

-- Seed Default Admin User (Password: Admin@123)
INSERT IGNORE INTO students (student_code, full_name, email, password_hash, department, semester, education_details, role)
VALUES (
    'ADMIN-001',
    'System Administrator',
    'admin@system.edu',
    'scrypt:32768:8:1$l8vK7pQ2mN9xR4tW$7e8a9c4b1d2f3e5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4',
    'Administration',
    0,
    'System Administration Account',
    'admin'
);