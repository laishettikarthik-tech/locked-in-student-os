import os
import secrets
from datetime import datetime, date
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, render_template, redirect, url_for, request, flash, send_from_directory, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_wtf.csrf import CSRFProtect
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import func

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {
    "pdf", "png", "jpg", "jpeg", "webp", "gif",
    "txt", "md", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "csv"
}
MAX_UPLOAD_MB = 20

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + str(BASE_DIR / "student_os.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
# Enable secure cookies when deployed behind HTTPS:
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("COOKIE_SECURE", "0") == "1"

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to access your workspace."
csrf = CSRFProtect(app)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    tasks = db.relationship("Task", backref="owner", lazy=True, cascade="all, delete-orphan")
    resources = db.relationship("Resource", backref="owner", lazy=True, cascade="all, delete-orphan")
    notes = db.relationship("Note", backref="owner", lazy=True, cascade="all, delete-orphan")
    focus_sessions = db.relationship("FocusSession", backref="owner", lazy=True, cascade="all, delete-orphan")
    screen_logs = db.relationship("ScreenLog", backref="owner", lazy=True, cascade="all, delete-orphan")
    quiz_results = db.relationship("QuizResult", backref="owner", lazy=True, cascade="all, delete-orphan")


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    subject = db.Column(db.String(100), default="")
    category = db.Column(db.String(40), default="College")
    priority = db.Column(db.String(20), default="Medium")
    status = db.Column(db.String(30), default="To Do")
    deadline = db.Column(db.Date, nullable=True)
    estimated_minutes = db.Column(db.Integer, default=30)
    description = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Resource(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    kind = db.Column(db.String(40), default="Useful link")
    subject = db.Column(db.String(100), default="")
    url = db.Column(db.String(1000), default="")
    stored_filename = db.Column(db.String(255), default="")
    original_filename = db.Column(db.String(255), default="")
    description = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    subject = db.Column(db.String(100), default="CSE")
    content = db.Column(db.Text, default="")
    image_filename = db.Column(db.String(255), default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class FocusSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    subject = db.Column(db.String(100), default="Study")
    minutes = db.Column(db.Integer, nullable=False)
    session_date = db.Column(db.Date, default=date.today, nullable=False)


class ScreenLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    app_name = db.Column(db.String(80), nullable=False)
    minutes = db.Column(db.Integer, nullable=False)
    log_date = db.Column(db.Date, default=date.today, nullable=False)


class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    title = db.Column(db.String(180), nullable=False)
    subject = db.Column(db.String(100), default="")
    score = db.Column(db.Integer, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    result_date = db.Column(db.Date, default=date.today, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def owned_or_404(model, record_id):
    record = db.session.get(model, record_id)
    if record is None or record.user_id != current_user.id:
        abort(404)
    return record


def safe_external_url(value):
    value = (value or "").strip()
    if not value:
        return ""
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("Links must begin with http:// or https://.")
    return value


@app.context_processor
def inject_globals():
    return {"today": date.today(), "current_year": date.today().year}


@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("landing.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(username) < 3 or len(username) > 40:
            flash("Username must be 3–40 characters.", "error")
        elif "@" not in email or len(email) > 254:
            flash("Enter a valid email address.", "error")
        elif len(password) < 12:
            flash("Use a password with at least 12 characters.", "error")
        elif password != confirm:
            flash("Passwords do not match.", "error")
        elif User.query.filter(func.lower(User.username) == username.lower()).first():
            flash("That username is already taken.", "error")
        elif User.query.filter_by(email=email).first():
            flash("An account with that email already exists.", "error")
        else:
            user = User(username=username, email=email, password_hash=generate_password_hash(password))
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Welcome! Your private workspace is ready.", "success")
            return redirect(url_for("dashboard"))
    return render_template("auth.html", mode="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        identity = request.form.get("identity", "").strip()
        password = request.form.get("password", "")
        user = User.query.filter(
            (func.lower(User.email) == identity.lower()) |
            (func.lower(User.username) == identity.lower())
        ).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=bool(request.form.get("remember")))
            flash("You're logged in.", "success")
            return redirect(url_for("dashboard"))
        flash("Invalid username/email or password.", "error")
    return render_template("auth.html", mode="login")


@app.post("/logout")
@login_required
def logout():
    logout_user()
    flash("You have logged out.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    total = len(tasks)
    completed = sum(t.status == "Completed" for t in tasks)
    active = sum(t.status in ("To Do", "In Progress") for t in tasks)
    overdue = sum(t.deadline and t.deadline < date.today() and t.status != "Completed" for t in tasks)
    focus_minutes = db.session.query(func.coalesce(func.sum(FocusSession.minutes), 0)).filter_by(
        user_id=current_user.id, session_date=date.today()).scalar()
    screen_minutes = db.session.query(func.coalesce(func.sum(ScreenLog.minutes), 0)).filter_by(
        user_id=current_user.id, log_date=date.today()).scalar()
    upcoming = Task.query.filter(
        Task.user_id == current_user.id,
        Task.deadline.isnot(None),
        Task.status != "Completed",
        Task.deadline >= date.today()
    ).order_by(Task.deadline.asc()).limit(5).all()
    return render_template("dashboard.html", total=total, completed=completed, active=active,
                           overdue=overdue, focus_minutes=focus_minutes, screen_minutes=screen_minutes,
                           upcoming=upcoming, completion_pct=round(completed / total * 100) if total else 0)


@app.route("/tasks", methods=["GET", "POST"])
@login_required
def tasks():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Task name is required.", "error")
            return redirect(url_for("tasks"))
        try:
            estimate = max(1, min(int(request.form.get("estimated_minutes", "30")), 10080))
        except ValueError:
            estimate = 30
        deadline_value = request.form.get("deadline", "").strip()
        try:
            deadline = date.fromisoformat(deadline_value) if deadline_value else None
        except ValueError:
            deadline = None
        category = request.form.get("category", "College")
        if category not in ["College", "Exam", "Internship", "Personal", "Project", "Other"]:
            category = "Other"
        priority = request.form.get("priority", "Medium")
        if priority not in ["Low", "Medium", "High", "Urgent"]:
            priority = "Medium"
        task = Task(user_id=current_user.id, title=title, subject=request.form.get("subject", "").strip()[:100],
                    category=category, priority=priority, status="To Do", deadline=deadline,
                    estimated_minutes=estimate, description=request.form.get("description", "").strip())
        db.session.add(task)
        db.session.commit()
        flash("Task added to your board.", "success")
        return redirect(url_for("tasks"))
    all_tasks = Task.query.filter_by(user_id=current_user.id).order_by(
        Task.deadline.is_(None), Task.deadline.asc(), Task.created_at.desc()).all()
    selected = request.args.get("view", "kanban")
    return render_template("tasks.html", tasks=all_tasks, view=selected)


@app.post("/tasks/<int:task_id>/status")
@login_required
def update_task_status(task_id):
    task = owned_or_404(Task, task_id)
    status = request.form.get("status")
    if status not in ["To Do", "In Progress", "Completed", "Incomplete"]:
        abort(400)
    task.status = status
    db.session.commit()
    flash("Task status updated.", "success")
    return redirect(request.referrer or url_for("tasks"))


@app.post("/tasks/<int:task_id>/delete")
@login_required
def delete_task(task_id):
    task = owned_or_404(Task, task_id)
    db.session.delete(task)
    db.session.commit()
    flash("Task deleted.", "success")
    return redirect(url_for("tasks"))


@app.route("/library", methods=["GET", "POST"])
@login_required
def library():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Resource title is required.", "error")
            return redirect(url_for("library"))
        try:
            url = safe_external_url(request.form.get("url", ""))
        except ValueError as exc:
            flash(str(exc), "error")
            return redirect(url_for("library"))
        file = request.files.get("file")
        stored = original = ""
        if file and file.filename:
            if not allowed_file(file.filename):
                flash("That file type is not allowed.", "error")
                return redirect(url_for("library"))
            original = secure_filename(file.filename)[:255]
            stored = f"{current_user.id}_{secrets.token_hex(16)}_{original}"
            file.save(UPLOAD_DIR / stored)
        kind = request.form.get("kind", "Useful link")
        allowed_kinds = ["Question paper", "Midsem paper", "Semester paper", "External paper",
                         "Assignment", "Internship", "Useful link", "Personal link", "Image", "Other"]
        if kind not in allowed_kinds:
            kind = "Other"
        resource = Resource(user_id=current_user.id, title=title, kind=kind,
                            subject=request.form.get("subject", "").strip()[:100],
                            url=url, stored_filename=stored, original_filename=original,
                            description=request.form.get("description", "").strip())
        db.session.add(resource)
        db.session.commit()
        flash("Resource saved to your library.", "success")
        return redirect(url_for("library"))
    resources = Resource.query.filter_by(user_id=current_user.id).order_by(Resource.created_at.desc()).all()
    return render_template("library.html", resources=resources)


@app.get("/files/<int:resource_id>")
@login_required
def download_resource(resource_id):
    resource = owned_or_404(Resource, resource_id)
    if not resource.stored_filename:
        abort(404)
    return send_from_directory(UPLOAD_DIR, resource.stored_filename,
                               as_attachment=True, download_name=resource.original_filename)


@app.post("/library/<int:resource_id>/delete")
@login_required
def delete_resource(resource_id):
    resource = owned_or_404(Resource, resource_id)
    if resource.stored_filename:
        try:
            (UPLOAD_DIR / resource.stored_filename).unlink(missing_ok=True)
        except OSError:
            pass
    db.session.delete(resource)
    db.session.commit()
    flash("Resource deleted.", "success")
    return redirect(url_for("library"))


@app.route("/notes", methods=["GET", "POST"])
@login_required
def notes():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        if not title:
            flash("Note title is required.", "error")
            return redirect(url_for("notes"))
        image = request.files.get("image")
        image_filename = ""
        if image and image.filename:
            if not allowed_file(image.filename) or image.filename.rsplit(".", 1)[-1].lower() not in {"png", "jpg", "jpeg", "webp", "gif"}:
                flash("Note images must be PNG, JPG, JPEG, WEBP, or GIF.", "error")
                return redirect(url_for("notes"))
            safe_name = secure_filename(image.filename)[:180]
            image_filename = f"{current_user.id}_{secrets.token_hex(16)}_{safe_name}"
            image.save(UPLOAD_DIR / image_filename)
        subject = request.form.get("subject", "CSE")
        if subject not in ["CSE", "Mechanical", "Electrical", "Robotics", "AI & ML", "Mathematics", "Other"]:
            subject = "Other"
        note = Note(user_id=current_user.id, title=title, subject=subject,
                    content=request.form.get("content", "").strip(), image_filename=image_filename)
        db.session.add(note)
        db.session.commit()
        flash("Note saved.", "success")
        return redirect(url_for("notes"))
    all_notes = Note.query.filter_by(user_id=current_user.id).order_by(Note.created_at.desc()).all()
    return render_template("notes.html", notes=all_notes)


@app.get("/note-images/<int:note_id>")
@login_required
def note_image(note_id):
    note = owned_or_404(Note, note_id)
    if not note.image_filename:
        abort(404)
    return send_from_directory(UPLOAD_DIR, note.image_filename, as_attachment=False)


@app.post("/notes/<int:note_id>/delete")
@login_required
def delete_note(note_id):
    note = owned_or_404(Note, note_id)
    if note.image_filename:
        try:
            (UPLOAD_DIR / note.image_filename).unlink(missing_ok=True)
        except OSError:
            pass
    db.session.delete(note)
    db.session.commit()
    flash("Note deleted.", "success")
    return redirect(url_for("notes"))


@app.route("/focus", methods=["GET", "POST"])
@login_required
def focus():
    if request.method == "POST":
        try:
            minutes = int(request.form.get("minutes", "0"))
        except ValueError:
            minutes = 0
        subject = request.form.get("subject", "Study").strip()[:100] or "Study"
        if not 1 <= minutes <= 1440:
            flash("Study time must be between 1 and 1440 minutes.", "error")
        else:
            db.session.add(FocusSession(user_id=current_user.id, subject=subject, minutes=minutes))
            db.session.commit()
            flash(f"Saved {minutes} focused minutes.", "success")
        return redirect(url_for("focus"))
    sessions = FocusSession.query.filter_by(user_id=current_user.id).order_by(FocusSession.session_date.desc(), FocusSession.id.desc()).limit(20).all()
    total = db.session.query(func.coalesce(func.sum(FocusSession.minutes), 0)).filter_by(user_id=current_user.id).scalar()
    today_total = db.session.query(func.coalesce(func.sum(FocusSession.minutes), 0)).filter_by(
        user_id=current_user.id, session_date=date.today()).scalar()
    return render_template("focus.html", sessions=sessions, total=total, today_total=today_total)


@app.route("/screen-time", methods=["GET", "POST"])
@login_required
def screen_time():
    if request.method == "POST":
        app_name = request.form.get("app_name", "").strip()[:80]
        try:
            minutes = int(request.form.get("minutes", "0"))
        except ValueError:
            minutes = 0
        if not app_name or not 1 <= minutes <= 1440:
            flash("Enter an app name and minutes between 1 and 1440.", "error")
        else:
            db.session.add(ScreenLog(user_id=current_user.id, app_name=app_name, minutes=minutes))
            db.session.commit()
            flash("Screen-time entry saved.", "success")
        return redirect(url_for("screen_time"))
    logs = ScreenLog.query.filter_by(user_id=current_user.id).order_by(ScreenLog.log_date.desc(), ScreenLog.id.desc()).limit(50).all()
    today_total = db.session.query(func.coalesce(func.sum(ScreenLog.minutes), 0)).filter_by(
        user_id=current_user.id, log_date=date.today()).scalar()
    today_focus = db.session.query(func.coalesce(func.sum(FocusSession.minutes), 0)).filter_by(
        user_id=current_user.id, session_date=date.today()).scalar()
    return render_template("screen_time.html", logs=logs, today_total=today_total, today_focus=today_focus)


@app.route("/scores", methods=["GET", "POST"])
@login_required
def scores():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        subject = request.form.get("subject", "").strip()[:100]
        try:
            score = int(request.form.get("score", "0"))
            total = int(request.form.get("total", "0"))
        except ValueError:
            score = total = 0
        if not title or total < 1 or score < 0 or score > total:
            flash("Enter a title and a valid score (0 to total marks).", "error")
        else:
            db.session.add(QuizResult(user_id=current_user.id, title=title, subject=subject, score=score, total=total))
            db.session.commit()
            flash("Score saved.", "success")
        return redirect(url_for("scores"))
    results = QuizResult.query.filter_by(user_id=current_user.id).order_by(QuizResult.result_date.desc(), QuizResult.id.desc()).all()
    total_scored = sum(r.score for r in results)
    total_marks = sum(r.total for r in results)
    percentage = round(total_scored / total_marks * 100, 1) if total_marks else 0
    return render_template("scores.html", results=results, total_scored=total_scored,
                           total_marks=total_marks, percentage=percentage)


@app.errorhandler(413)
def too_large(_error):
    flash(f"Files must be {MAX_UPLOAD_MB} MB or smaller.", "error")
    return redirect(request.referrer or url_for("library"))


with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
