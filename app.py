# app.py (replace existing file)
import os
import json
from pathlib import Path
from flask import (
    Flask, request, jsonify, send_from_directory, session, redirect, url_for
)
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../Frontend")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PROJECTS_FILE = os.path.join(BASE_DIR, "projects.json")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path="")

# Config: read secrets from environment
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "emxelux")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-this-in-prod")

# Upload limits + allowed extensions
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
ALLOWED_ZIP_EXTS = {".zip"}

def allowed_file(filename, allowed_exts):
    if not filename:
        return False
    ext = Path(filename).suffix.lower()
    return ext in allowed_exts

def load_projects():
    if not os.path.exists(PROJECTS_FILE):
        return []
    with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            # corrupted file: treat as empty or recreate
            return []

def save_projects(projects):
    tmp = PROJECTS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2)
    os.replace(tmp, PROJECTS_FILE)

# Simple admin login route (for demo only)
@app.route("/login", methods=["POST"])
def login():
    data = request.json or {}
    username = data.get("username")
    password = data.get("password")
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["logged_in"] = True
        return jsonify({"message": "Logged in"})
    return jsonify({"error": "Unauthorized"}), 401

@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})

# Example: add project with file upload
@app.route("/add_project", methods=["POST"])
def add_project():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    # Use form fields and files (adjust depending on frontend)
    title = request.form.get("title", "")
    description = request.form.get("description", "")
    image = request.files.get("image")
    zip_file = request.files.get("zip")

    saved_image_name = None
    saved_zip_name = None

    # handle image
    if image and allowed_file(image.filename, ALLOWED_IMAGE_EXTS):
        filename = secure_filename(image.filename)
        saved_image_name = f"{int(os.times()[4])}_{filename}"
        image.save(os.path.join(UPLOAD_DIR, saved_image_name))
    elif image:
        return jsonify({"error": "Invalid image file type"}), 400

    # handle zip
    if zip_file and allowed_file(zip_file.filename, ALLOWED_ZIP_EXTS):
        filename = secure_filename(zip_file.filename)
        saved_zip_name = f"{int(os.times()[4])}_{filename}"
        zip_file.save(os.path.join(UPLOAD_DIR, saved_zip_name))
    elif zip_file:
        return jsonify({"error": "Invalid zip file type"}), 400

    projects = load_projects()
    project = {
        "title": title,
        "description": description,
        "image": saved_image_name,
        "zip": saved_zip_name
    }
    projects.append(project)
    save_projects(projects)
    return jsonify({"message": "Project added", "project": project})

@app.route("/projects", methods=["GET"])
def list_projects():
    projects = load_projects()
    return jsonify(projects)

@app.route("/download/<filename>", methods=["GET"])
def download_file(filename):
    # sanitize the filename and ensure it exists in uploads
    safe = secure_filename(filename)
    path = os.path.join(UPLOAD_DIR, safe)
    if not os.path.exists(path):
        return jsonify({"error": "File not found"}), 404
    return send_from_directory(UPLOAD_DIR, safe, as_attachment=True)

@app.route("/delete_project/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    projects = load_projects()
    if project_id < 0 or project_id >= len(projects):
        return jsonify({'error': 'Invalid project ID'}), 404
    project = projects.pop(project_id)

    for filename in filter(None, [project.get("image"), project.get("zip")]):
        safe = secure_filename(filename)
        full = os.path.join(UPLOAD_DIR, safe)
        try:
            if os.path.exists(full):
                os.remove(full)
        except Exception as e:
            app.logger.exception("Error deleting file %s: %s", full, e)
    save_projects(projects)
    return jsonify({'message': 'Project deleted successfully!'})

if __name__ == "__main__":
    debug_env = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", debug=debug_env)
