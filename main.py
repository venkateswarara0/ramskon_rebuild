import os
import json
import requests
import urllib.parse
from uuid import uuid4
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

from db import get_connection

try:
    from groq import Groq
except ImportError:
    Groq = None

load_dotenv()

app = Flask(__name__, template_folder="app/templates", static_folder="app/static")
app.secret_key = os.getenv("SECRET_KEY", "fallback-secret-key")
app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_FOLDER", "app/static/uploads")
app.config["MAX_CONTENT_LENGTH"] = 200 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    "pdf", "jpg", "jpeg", "png", "mp4", "mp3",
    "doc", "docx", "txt", "zip"
}

COURSES_DATA = [
    ("Video Editing", "Learn editing fundamentals, storytelling, pacing, transitions, audio cleanup, reels workflow, client edits, and delivery.", "Creative & Agency Skills"),
    ("Graphic Designing", "Learn design principles, layout, typography, color, branding, social media creatives, and practical design workflow.", "Creative & Agency Skills"),
    ("Motion Graphics", "Learn animation basics, motion principles, title animation, transitions, promo videos, and content motion design.", "Creative & Agency Skills"),
    ("UI/UX Design", "Learn design thinking, wireframes, user flows, prototypes, research, UI systems, and practical product design.", "Creative & Agency Skills"),
    ("Thumbnail Designing", "Learn thumbnail psychology, CTR design, composition, contrast, visual hooks, and practical channel work.", "Creative & Agency Skills"),
    ("Social Media Content Creation", "Learn content ideas, scripting, hooks, content pillars, platform adaptation, and content planning.", "Creative & Agency Skills"),
    ("Generative AI", "Learn generative AI concepts, tools, prompt usage, image/text generation, and business use cases.", "AI & Tech Skills"),
    ("AI & Machine Learning Basics", "Learn ML foundations, supervised learning, models, data basics, training ideas, and beginner workflows.", "AI & Tech Skills"),
    ("AI Automation", "Learn automation with no-code tools like Zapier and Make, workflow logic, integrations, and business automation.", "AI & Tech Skills"),
    ("Prompt Engineering", "Learn structured prompts, context handling, system prompts, role prompting, chain prompting, and practical results.", "AI & Tech Skills"),
    ("ChatGPT & AI Tools Mastery", "Learn AI workflows, productivity systems, research usage, automation ideas, and client-facing use cases.", "AI & Tech Skills"),
    ("Web Development", "Learn frontend, backend, databases, APIs, auth, deployment, and real website building.", "Development Skills"),
    ("Python Programming", "Learn Python syntax, logic, loops, functions, files, OOP, APIs, and practical mini projects.", "Development Skills"),
    ("Full Stack Development", "Learn frontend, backend, database design, authentication, APIs, deployment, and full product workflow.", "Development Skills"),
    ("App Development", "Learn app basics, UI flow, backend integration, APIs, user experience, and deployment foundations.", "Development Skills"),
    ("Digital Marketing", "Learn funnels, offers, content, ads, branding, customer journey, analytics, and agency-oriented marketing.", "Marketing & Business Skills"),
    ("SEO", "Learn keyword research, on-page SEO, technical SEO, backlinks, content SEO, and ranking systems.", "Marketing & Business Skills"),
    ("Social Media Marketing", "Learn platform growth, strategy, brand content, ad basics, lead generation, and campaign planning.", "Marketing & Business Skills"),
    ("Freelancing & Personal Branding", "Learn client outreach, proposals, pricing, positioning, social proof, and personal brand building.", "Marketing & Business Skills"),
    ("Agency Building & Client Acquisition", "Learn service packaging, niche selection, lead generation, sales systems, onboarding, and delivery.", "Marketing & Business Skills"),
]

DAY_PHASES = [
    "Introduction and Meaning",
    "Foundations",
    "Core Concepts",
    "Tools and Setup",
    "Practical Basics",
    "Workflow Understanding",
    "Real World Use Cases",
    "Strategy Building",
    "Execution Basics",
    "Common Problems and Fixes",
    "Intermediate Concepts",
    "Optimization",
    "Client Perspective",
    "Planning and Systems",
    "Advanced Concepts",
    "Industry Standards",
    "Case Study Breakdown",
    "Implementation Practice",
    "Portfolio Thinking",
    "Communication and Delivery",
    "Pricing and Value",
    "Lead Generation",
    "Sales Process",
    "Conversion and Closing",
    "Project Delivery",
    "Quality Improvement",
    "Scaling Methods",
    "Brand Building",
    "System Building",
    "Final Capstone"
]


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def build_youtube_search_link(query):
    if not query:
        return ""
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)


def clean_topic_for_youtube(text):
    if not text:
        return ""
    return " ".join(text.replace("—", " ").replace(":", " ").split()).strip()


def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if api_key and Groq is not None:
        return Groq(api_key=api_key)
    return None


	


def generate_course_plan_with_groq(course_title, course_description):
    client = get_groq_client()

    fallback_plan = []
    for day_number, phase_title in enumerate(DAY_PHASES, start=1):
        fallback_plan.append({
            "day_number": day_number,
            "topic_title": f"Day {day_number}: {phase_title} in {course_title}",
            "topic_content": (
                f"What is this topic?\n"
                f"{phase_title} is an important part of {course_title}. Today you should understand what it means, "
                f"why it matters, and how it is used in practical work.\n\n"
                f"Why is it important?\n"
                f"This topic supports the overall goal of the course: {course_description}\n\n"
                f"Practical understanding:\n"
                f"Do not study it only as theory. Think about how this concept is applied in real client work, "
                f"projects, business workflow, service delivery, or portfolio building.\n\n"
                f"Real-world example:\n"
                f"Imagine using this concept in an actual {course_title} situation. Your focus today is to understand "
                f"the logic, execution flow, and outcome.\n\n"
                f"Day goal:\n"
                f"By the end of Day {day_number}, you should be able to explain this topic in your own words and apply it practically."
            ),
            "assignment_text": (
                f"Day {day_number} Assignment:\n"
                f"1. Explain what '{phase_title}' means in {course_title}.\n"
                f"2. Write why it is important.\n"
                f"3. Give one real example.\n"
                f"4. Create a small proof of work, notes, checklist, mini-plan, or demo related to this topic.\n"
                f"5. Submit your explanation and practical output."
            ),
            "youtube_query_en": f"{course_title} {phase_title} tutorial english",
            "youtube_query_te": f"{course_title} {phase_title} tutorial telugu"
        })

    if client is None:
        return fallback_plan

    phases_text = "\n".join([f"Day {i+1}: {phase}" for i, phase in enumerate(DAY_PHASES)])

    prompt = f"""
You are creating a premium 30-day course roadmap.

Course Title: {course_title}
Course Description: {course_description}

Use these exact 30 day phases in order:
{phases_text}

Return ONLY valid JSON array with exactly 30 objects.

Each object must have:
day_number
topic_title
topic_content
assignment_text
youtube_query_en
youtube_query_te

Rules:
- Keep all 30 days unique
- topic_title must be specific and not generic
- topic_content must clearly explain:
  1. what it is
  2. why it matters
  3. one practical understanding
  4. one real-world example
- assignment_text must be practical for that day
- youtube_query_en must be a good English tutorial search
- youtube_query_te must be a good Telugu tutorial search
- no markdown
- no extra text
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            temperature=0.5,
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content.strip()
        plan = json.loads(content)

        if not isinstance(plan, list) or len(plan) != 30:
            return fallback_plan

        normalized = []
        for i, item in enumerate(plan, start=1):
            normalized.append({
                "day_number": int(item.get("day_number", i)),
                "topic_title": str(item.get("topic_title", f"Day {i}: {DAY_PHASES[i-1]} in {course_title}")).strip(),
                "topic_content": str(item.get("topic_content", fallback_plan[i-1]["topic_content"])).strip(),
                "assignment_text": str(item.get("assignment_text", fallback_plan[i-1]["assignment_text"])).strip(),
                "youtube_query_en": str(item.get("youtube_query_en", fallback_plan[i-1]["youtube_query_en"])).strip(),
                "youtube_query_te": str(item.get("youtube_query_te", fallback_plan[i-1]["youtube_query_te"])).strip(),
            })

        return normalized

    except Exception as e:
        print("Groq bulk generation error:", str(e))
        return fallback_plan


def fetch_youtube_videos(course_title, topic_title, preferred_language="english", max_results=3):
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()
    if not api_key:
        return []

    language_code = "te" if preferred_language == "telugu" else "en"
    cleaned_topic = clean_topic_for_youtube(topic_title)

    english_queries = [
        f"{course_title} {cleaned_topic} tutorial",
        f"{cleaned_topic} tutorial",
        f"{course_title} {cleaned_topic} explained",
        f"{cleaned_topic} for beginners"
    ]

    telugu_queries = [
        f"{course_title} {cleaned_topic} tutorial telugu",
        f"{cleaned_topic} tutorial telugu",
        f"{course_title} {cleaned_topic} explained telugu",
        f"{cleaned_topic} for beginners telugu"
    ]

    queries = telugu_queries if preferred_language == "telugu" else english_queries

    search_attempts = []
    for q in queries:
        search_attempts.append({
            "q": q,
            "relevanceLanguage": language_code,
            "videoEmbeddable": "true",
            "videoSyndicated": "true",
        })
        search_attempts.append({
            "q": q,
            "relevanceLanguage": language_code,
            "videoEmbeddable": "true",
        })
        search_attempts.append({
            "q": q,
            "videoEmbeddable": "true",
        })

    for params_extra in search_attempts:
        try:
            params = {
                "part": "snippet",
                "type": "video",
                "maxResults": max_results,
                "key": api_key,
            }
            params.update(params_extra)

            response = requests.get(
                "https://www.googleapis.com/youtube/v3/search",
                params=params,
                timeout=15
            )
            response.raise_for_status()
            data = response.json()

            videos = []
            for item in data.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                snippet = item.get("snippet", {})
                if video_id:
                    videos.append({
                        "title": snippet.get("title", "Video"),
                        "channel": snippet.get("channelTitle", ""),
                        "watch_url": f"https://www.youtube.com/watch?v={video_id}",
                        "embed_url": f"https://www.youtube.com/embed/{video_id}",
                        "thumbnail": snippet.get("thumbnails", {}).get("high", {}).get("url", "")
                    })

            if videos:
                return videos

        except Exception as e:
            print("YouTube API error:", str(e))

    return []


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            flash("Access denied.", "danger")
            return redirect(url_for("user_dashboard"))
        return f(*args, **kwargs)
    return decorated_function


def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please login first.", "warning")
            return redirect(url_for("login"))
        if session.get("role") != "user":
            flash("Access denied.", "danger")
            return redirect(url_for("admin_dashboard"))
        return f(*args, **kwargs)
    return decorated_function


def create_admin_if_not_exists():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE email = %s", ("admin@ramskon.com",))
    admin = cursor.fetchone()

    if not admin:
        password_hash = generate_password_hash("admin123")
        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role, preferred_language)
            VALUES (%s, %s, %s, %s, %s)
            """,
            ("Admin", "admin@ramskon.com", password_hash, "admin", "english")
        )
        conn.commit()

    conn.close()


def seed_courses():
    conn = get_connection()
    cursor = conn.cursor()

    for title, description, category in COURSES_DATA:
        cursor.execute("SELECT id FROM courses WHERE title = %s", (title,))
        existing = cursor.fetchone()

        if not existing:
            cursor.execute(
                """
                INSERT INTO courses (title, description, duration_days, category)
                VALUES (%s, %s, %s, %s)
                """,
                (title, description, 30, category)
            )

    conn.commit()
    conn.close()


def user_has_approved_course(user_id, course_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id
        FROM course_requests
        WHERE user_id = %s AND course_id = %s AND status = 'approved'
        """,
        (user_id, course_id)
    )
    approved = cursor.fetchone()
    conn.close()
    return approved is not None


def get_unlocked_day(user_id, course_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT COUNT(*) AS completed_days
        FROM assignment_submissions
        WHERE user_id = %s AND course_id = %s
        """,
        (user_id, course_id)
    )
    row = cursor.fetchone()
    conn.close()
    completed_days = row.completed_days if row else 0
    return completed_days + 1


@app.route("/healthz")
def healthz():
    return {"status": "ok"}, 200


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not full_name or not email or not password or not confirm_password:
            flash("All fields are required.", "danger")
            return render_template("auth/register.html")

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/register.html")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()

        if existing_user:
            conn.close()
            flash("Email already registered.", "danger")
            return render_template("auth/register.html")

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO users (full_name, email, password_hash, role, preferred_language)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (full_name, email, password_hash, "user", "english")
        )
        conn.commit()
        conn.close()

        flash("Registration successful. Please login.", "success")
        return redirect(url_for("login"))

    return render_template("auth/register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        if session.get("role") == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "").strip()

        if not email or not password:
            flash("Email and password are required.", "danger")
            return render_template("auth/login.html")

        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT id, full_name, email, password_hash, role, preferred_language
            FROM users
            WHERE email = %s
            """,
            (email,)
        )
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["full_name"] = user.full_name
            session["email"] = user.email
            session["role"] = user.role
            session["preferred_language"] = user.preferred_language

            flash("Login successful.", "success")

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))
            return redirect(url_for("user_dashboard"))

        flash("Invalid email or password.", "danger")

    return render_template("auth/login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully.", "success")
    return redirect(url_for("login"))


@app.route("/user/set-language", methods=["POST"])
@user_required
def set_language():
    language = request.form.get("preferred_language", "english").strip().lower()
    if language not in ["english", "telugu"]:
        flash("Invalid language.", "danger")
        return redirect(url_for("user_dashboard"))

    user_id = session.get("user_id")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET preferred_language = %s WHERE id = %s",
        (language, user_id)
    )
    conn.commit()
    conn.close()

    session["preferred_language"] = language
    flash("Preferred language updated.", "success")
    return redirect(url_for("user_dashboard"))


@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) AS total_users FROM users WHERE role = 'user'")
    total_users = cursor.fetchone().total_users

    cursor.execute("SELECT COUNT(*) AS total_courses FROM courses")
    total_courses = cursor.fetchone().total_courses

    cursor.execute("SELECT COUNT(*) AS pending_requests FROM course_requests WHERE status = 'pending'")
    pending_requests = cursor.fetchone().pending_requests

    cursor.execute("SELECT COUNT(*) AS total_days FROM course_days")
    total_days = cursor.fetchone().total_days

    conn.close()

    return render_template(
        "admin/dashboard.html",
        total_users=total_users,
        total_courses=total_courses,
        pending_requests=pending_requests,
        total_days=total_days
    )


@app.route("/admin/requests")
@admin_required
def admin_requests():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            cr.id,
            u.full_name,
            u.email,
            c.title,
            cr.status,
            cr.requested_at
        FROM course_requests cr
        INNER JOIN users u ON cr.user_id = u.id
        INNER JOIN courses c ON cr.course_id = c.id
        ORDER BY cr.id DESC
        """
    )
    requests_data = cursor.fetchall()
    conn.close()

    return render_template("admin/requests.html", requests_data=requests_data)


@app.route("/admin/requests/<int:request_id>/<action>", methods=["POST"])
@admin_required
def update_request_status(request_id, action):
    if action not in ["approve", "reject"]:
        flash("Invalid action.", "danger")
        return redirect(url_for("admin_requests"))

    new_status = "approved" if action == "approve" else "rejected"

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        UPDATE course_requests
        SET status = %s, reviewed_at = NOW()
        WHERE id = %s
        """,
        (new_status, request_id)
    )
    conn.commit()
    conn.close()

    flash(f"Request {new_status} successfully.", "success")
    return redirect(url_for("admin_requests"))


@app.route("/admin/generate-days", methods=["GET", "POST"])
@admin_required
def admin_generate_days():
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, title, description FROM courses ORDER BY title ASC")
        courses = cursor.fetchall()

        if request.method == "POST":
            course_id_raw = request.form.get("course_id", "").strip()

            if not course_id_raw.isdigit():
                flash("Invalid course selection.", "danger")
                conn.close()
                return redirect(url_for("admin_generate_days"))

            course_id = int(course_id_raw)

            cursor.execute(
                "SELECT id, title, description FROM courses WHERE id = %s",
                (course_id,)
            )
            course = cursor.fetchone()

            if not course:
                conn.close()
                flash("Course not found.", "danger")
                return redirect(url_for("admin_generate_days"))

            cursor.execute("DELETE FROM course_days WHERE course_id = %s", (course_id,))
            conn.commit()

            plan = generate_course_plan_with_groq(course.title, course.description)

            for item in plan:
                cursor.execute(
                    """
                    INSERT INTO course_days
                    (course_id, day_number, topic_title, topic_content, assignment_text, youtube_query_en, youtube_query_te)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        course_id,
                        item["day_number"],
                        item["topic_title"],
                        item["topic_content"],
                        item["assignment_text"],
                        item["youtube_query_en"],
                        item["youtube_query_te"]
                    )
                )

            conn.commit()
            conn.close()

            flash("30-day AI plan generated successfully.", "success")
            return redirect(url_for("admin_generate_days"))

        conn.close()
        return render_template("admin/generate_days.html", courses=courses)

    except Exception as e:
        conn.rollback()
        conn.close()
        print("ADMIN_GENERATE_DAYS_ERROR:", str(e))
        flash(f"Generate days failed: {str(e)}", "danger")
        return redirect(url_for("admin_generate_days"))
        
	conn.close()
        return render_template("admin/generate_days.html", courses=courses)



@app.route("/admin/progress")
@admin_required
def admin_progress():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            u.full_name,
            u.email,
            c.title AS course_title,
            COUNT(s.id) AS completed_days
        FROM course_requests cr
        INNER JOIN users u ON cr.user_id = u.id
        INNER JOIN courses c ON cr.course_id = c.id
        LEFT JOIN assignment_submissions s
            ON s.user_id = u.id AND s.course_id = c.id
        WHERE cr.status = 'approved'
        GROUP BY u.full_name, u.email, c.title
        ORDER BY u.full_name, c.title
        """
    )
    rows = cursor.fetchall()
    conn.close()

    progress_rows = []
    for row in rows:
        progress_percent = int((row.completed_days / 30) * 100)
        progress_rows.append({
            "full_name": row.full_name,
            "email": row.email,
            "course_title": row.course_title,
            "completed_days": row.completed_days,
            "remaining_days": 30 - row.completed_days,
            "progress_percent": progress_percent
        })

    return render_template("admin/progress.html", progress_rows=progress_rows)


@app.route("/admin/submissions")
@admin_required
def admin_submissions():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            s.id,
            u.full_name,
            u.email,
            c.title AS course_title,
            s.day_number,
            s.submission_text,
            s.file_name,
            s.file_path,
            s.file_type,
            s.admin_review_status,
            s.admin_review_note,
            s.submitted_at
        FROM assignment_submissions s
        INNER JOIN users u ON s.user_id = u.id
        INNER JOIN courses c ON s.course_id = c.id
        ORDER BY s.submitted_at DESC
        """
    )
    submissions = cursor.fetchall()
    conn.close()

    return render_template("admin/submissions.html", submissions=submissions)


@app.route("/admin/submissions/<int:submission_id>/review", methods=["POST"])
@admin_required
def admin_review_submission(submission_id):
    review_status = request.form.get("admin_review_status", "pending").strip().lower()
    review_note = request.form.get("admin_review_note", "").strip()

    if review_status not in ["pending", "approved", "needs_changes"]:
        flash("Invalid review status.", "danger")
        return redirect(url_for("admin_submissions"))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE assignment_submissions
        SET admin_review_status = %s, admin_review_note = %s
        WHERE id = %s
        """,
        (review_status, review_note or None, submission_id)
    )
    conn.commit()
    conn.close()

    flash("Submission review updated.", "success")
    return redirect(url_for("admin_submissions"))


@app.route("/user/dashboard")
@user_required
def user_dashboard():
    user_id = session.get("user_id")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            c.id,
            c.title,
            c.description,
            c.duration_days,
            c.category
        FROM course_requests cr
        INNER JOIN courses c ON cr.course_id = c.id
        WHERE cr.user_id = %s AND cr.status = 'approved'
        ORDER BY c.title ASC
        """,
        (user_id,)
    )
    approved_courses = cursor.fetchall()

    course_cards = []
    for course in approved_courses:
        unlocked_day = get_unlocked_day(user_id, course.id)

        cursor.execute(
            """
            SELECT COUNT(*) AS total_days
            FROM course_days
            WHERE course_id = %s
            """,
            (course.id,)
        )
        total_days_row = cursor.fetchone()
        total_days = total_days_row.total_days if total_days_row else 0

        completed_days = max(unlocked_day - 1, 0)
        progress_percent = int((completed_days / 30) * 100) if total_days else 0

        course_cards.append({
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "duration_days": course.duration_days,
            "category": course.category,
            "unlocked_day": unlocked_day if unlocked_day <= 30 else 30,
            "completed_days": completed_days,
            "progress_percent": progress_percent
        })

    conn.close()
    return render_template("user/dashboard.html", approved_courses=course_cards)


@app.route("/user/progress")
@user_required
def user_progress():
    user_id = session.get("user_id")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT
            c.id,
            c.title,
            c.category,
            COUNT(s.id) AS completed_days
        FROM course_requests cr
        INNER JOIN courses c ON cr.course_id = c.id
        LEFT JOIN assignment_submissions s
            ON s.course_id = c.id AND s.user_id = %s
        WHERE cr.user_id = %s AND cr.status = 'approved'
        GROUP BY c.id, c.title, c.category
        ORDER BY c.title
        """,
        (user_id, user_id)
    )
    rows = cursor.fetchall()
    conn.close()

    progress_rows = []
    for row in rows:
        progress_rows.append({
            "course_id": row.id,
            "course_title": row.title,
            "category": row.category,
            "completed_days": row.completed_days,
            "remaining_days": 30 - row.completed_days,
            "progress_percent": int((row.completed_days / 30) * 100)
        })

    return render_template("user/progress.html", progress_rows=progress_rows)


@app.route("/user/courses")
@user_required
def user_courses():
    user_id = session.get("user_id")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT
            c.id,
            c.title,
            c.description,
            c.duration_days,
            c.category,
            cr.status
        FROM courses c
        LEFT JOIN course_requests cr
            ON c.id = cr.course_id AND cr.user_id = %s
        ORDER BY c.title ASC
        """,
        (user_id,)
    )
    courses = cursor.fetchall()
    conn.close()

    return render_template("user/courses.html", courses=courses)


@app.route("/user/request-course/<int:course_id>", methods=["POST"])
@user_required
def request_course(course_id):
    user_id = session.get("user_id")

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    valid_user = cursor.fetchone()

    if not valid_user:
        conn.close()
        session.clear()
        flash("Your session expired. Please login again.", "danger")
        return redirect(url_for("login"))

    cursor.execute("SELECT id FROM courses WHERE id = %s", (course_id,))
    valid_course = cursor.fetchone()

    if not valid_course:
        conn.close()
        flash("Course not found.", "danger")
        return redirect(url_for("user_courses"))

    cursor.execute(
        """
        SELECT id
        FROM course_requests
        WHERE user_id = %s AND course_id = %s
        """,
        (user_id, course_id)
    )
    existing = cursor.fetchone()

    if existing:
        conn.close()
        flash("You have already requested this course.", "warning")
        return redirect(url_for("user_courses"))

    cursor.execute(
        """
        INSERT INTO course_requests (user_id, course_id, status)
        VALUES (%s, %s, 'pending')
        """,
        (user_id, course_id)
    )
    conn.commit()
    conn.close()

    flash("Course request sent to admin.", "success")
    return redirect(url_for("user_courses"))


@app.route("/user/course/<int:course_id>")
@user_required
def user_course_detail(course_id):
    user_id = session.get("user_id")
    preferred_language = session.get("preferred_language", "english")

    if not user_has_approved_course(user_id, course_id):
        flash("This course is not approved for you.", "danger")
        return redirect(url_for("user_dashboard"))

    unlocked_day = get_unlocked_day(user_id, course_id)

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT id, title, description, duration_days, category
        FROM courses
        WHERE id = %s
        """,
        (course_id,)
    )
    course = cursor.fetchone()

    cursor.execute(
        """
        SELECT
            cd.day_number,
            cd.topic_title,
            cd.topic_content,
            cd.assignment_text,
            cd.youtube_query_en,
            cd.youtube_query_te,
            CASE
                WHEN s.id IS NOT NULL THEN 1
                ELSE 0
            END AS is_completed,
            s.file_name,
            s.file_path,
            s.submission_text,
            s.admin_review_status,
            s.admin_review_note
        FROM course_days cd
        LEFT JOIN assignment_submissions s
            ON cd.course_id = s.course_id
            AND cd.day_number = s.day_number
            AND s.user_id = %s
        WHERE cd.course_id = %s
        ORDER BY cd.day_number ASC
        """,
        (user_id, course_id)
    )
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        flash("This course has no generated 30-day plan yet. Ask admin to generate it in AI Planner.", "warning")
        return render_template(
            "user/course_detail.html",
            course=course,
            days=[],
            unlocked_day=1,
            preferred_language=preferred_language
        )

    days = []
    for row in rows:
        videos = []
        english_search_url = build_youtube_search_link(row.youtube_query_en or "")
        telugu_search_url = build_youtube_search_link(row.youtube_query_te or "")

        if row.day_number <= unlocked_day or row.is_completed == 1:
            if preferred_language == "telugu":
                videos = fetch_youtube_videos(course.title, row.topic_title, preferred_language="telugu", max_results=3)
                if not videos:
                    videos = fetch_youtube_videos(course.title, row.topic_title, preferred_language="english", max_results=3)
            else:
                videos = fetch_youtube_videos(course.title, row.topic_title, preferred_language="english", max_results=3)
                if not videos:
                    videos = fetch_youtube_videos(course.title, row.topic_title, preferred_language="telugu", max_results=3)

        days.append({
            "day_number": row.day_number,
            "topic_title": row.topic_title,
            "topic_content": row.topic_content,
            "assignment_text": row.assignment_text,
            "is_completed": row.is_completed,
            "file_name": row.file_name,
            "file_path": row.file_path,
            "submission_text": row.submission_text,
            "admin_review_status": row.admin_review_status,
            "admin_review_note": row.admin_review_note,
            "videos": videos,
            "english_search_url": english_search_url,
            "telugu_search_url": telugu_search_url
        })

    return render_template(
        "user/course_detail.html",
        course=course,
        days=days,
        unlocked_day=unlocked_day,
        preferred_language=preferred_language
    )


@app.route("/user/submit-assignment/<int:course_id>/<int:day_number>", methods=["POST"])
@user_required
def submit_assignment(course_id, day_number):
    user_id = session.get("user_id")

    if not user_has_approved_course(user_id, course_id):
        flash("This course is not approved for you.", "danger")
        return redirect(url_for("user_dashboard"))

    unlocked_day = get_unlocked_day(user_id, course_id)

    if day_number != unlocked_day:
        flash("You can only submit the currently unlocked day.", "danger")
        return redirect(url_for("user_course_detail", course_id=course_id))

    submission_text = request.form.get("submission_text", "").strip()
    uploaded_file = request.files.get("submission_file")

    if not submission_text and (not uploaded_file or uploaded_file.filename == ""):
        flash("Submit text or upload a file.", "danger")
        return redirect(url_for("user_course_detail", course_id=course_id))

    file_name = None
    file_path = None
    file_type = None

    if uploaded_file and uploaded_file.filename:
        if not allowed_file(uploaded_file.filename):
            flash("Unsupported file type.", "danger")
            return redirect(url_for("user_course_detail", course_id=course_id))

        os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
        safe_name = secure_filename(uploaded_file.filename)
        extension = safe_name.rsplit(".", 1)[1].lower()
        final_name = f"{uuid4().hex}.{extension}"
        absolute_path = os.path.join(app.config["UPLOAD_FOLDER"], final_name)
        uploaded_file.save(absolute_path)

        file_name = safe_name
        file_path = f"uploads/{final_name}"
        file_type = extension

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO assignment_submissions
        (user_id, course_id, day_number, submission_text, file_name, file_path, file_type, status, admin_review_status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'submitted', 'pending')
        """,
        (user_id, course_id, day_number, submission_text or None, file_name, file_path, file_type)
    )
    conn.commit()
    conn.close()

    flash(f"Day {day_number} submitted successfully. Next day unlocked.", "success")
    return redirect(url_for("user_course_detail", course_id=course_id))


if __name__ == "__main__":
    create_admin_if_not_exists()
    seed_courses()
    app.run(debug=True)