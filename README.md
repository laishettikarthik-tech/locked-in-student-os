# Locked In — Student OS

A local-first student productivity web app built with Flask, SQLite, HTML, CSS, and JavaScript.

## Features
- Account registration and login; password hashes (never plain-text passwords)
- Per-user private tasks with four statuses: To Do, In Progress, Completed, Incomplete
- Kanban board and list view
- Categories for college, exams, internship, personal tasks, and projects
- Priorities, deadlines, estimated minutes, descriptions, and overdue indicators
- Resource library for links, question papers, midsem/semester/external papers, assignments, internship files, and images
- Engineering notes for CSE, Mechanical, Electrical, Robotics, AI/ML, and Mathematics
- Focus timer and saved focus sessions
- Manual screen-time tracking
- Quiz and practice-score history
- CSRF protection, secure password hashing, per-user record checks, upload allowlist, and 20 MB upload cap

## Run on macOS
1. Install Python 3.10+ if needed.
2. Open Terminal and move into this folder:
   ```bash
   cd locked_in_student_os
   ```
3. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
4. Install packages:
   ```bash
   pip install -r requirements.txt
   ```
5. Set a stable secret key for your local environment:
   ```bash
   export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
   ```
   Keep the key private. For future sessions, set it again or store it in a local `.env` file using a dotenv package (not included by default).
6. Start the app:
   ```bash
   python app.py
   ```
7. Open http://127.0.0.1:5000 in your browser and create an account.

## Important notes
- The SQLite database (`student_os.db`) is created automatically in this project folder.
- Uploads are stored locally in `uploads/`. Back up the database and uploads folder together.
- The focus timer runs in the browser tab; log the minutes actually focused using the form.
- Screen-time logging is manual in this version. A normal web app cannot automatically read Instagram/Snapchat usage from your device without a supported OS integration and permissions.
- This is a student-project starter, not a fully audited production service. Before exposing it to the public internet, configure HTTPS, a persistent secret key, secure cookies (`COOKIE_SECURE=1` behind HTTPS), backups, rate limiting, email verification/password reset, and production hosting. Do not use Flask's development server for public production deployment.
- Never commit `student_os.db`, real uploaded files, secrets, or your `.venv` folder to GitHub.
