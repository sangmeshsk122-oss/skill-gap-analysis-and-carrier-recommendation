# Skill Gap Analysis & Career Recommendation System

## Run the configured Windows installation

MySQL Server 8.4 is installed as the automatic `MySQL84` Windows service. Its data is in `%LOCALAPPDATA%\SkillMatrixMySQL\data`; the schema is imported and the project's `.env` is configured.

If MySQL is stopped, open an Administrator Command Prompt and run:

```cmd
sc.exe start MySQL84
```

If the service has not been installed, run `setup-mysql-service.cmd` as Administrator once.

Start Flask:

```powershell
python app.py
```

Open http://127.0.0.1:5000.

The MySQL root password is stored locally in `%LOCALAPPDATA%\SkillMatrixMySQL\root-password.txt`; the application database credentials are in `.env`.

## AI skill quizzes

The assessment page provides a separate quiz for each skill, with five sequential levels and 20 fixed questions per level. Passing requires at least 14 correct answers. The built-in question bank is cached in MySQL; questions are prepared locally and no external AI API or API key is required.

For an existing installation, re-run `database.sql` with database-admin privileges to create the quiz progress and question-bank tables.

## Fresh setup

Install Python 3.12+ and MySQL Server 8.4, then:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Configure `.env` with the MySQL credentials. Start MySQL, then import `database.sql` as a MySQL administrator before running `python app.py`.

Administrator account: `admin@system.edu`, with the password set in the `ADMIN_PASSWORD` environment variable.
