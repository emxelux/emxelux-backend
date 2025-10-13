import os
import json
from flask import Flask, request, jsonify, send_from_directory, session, redirect, url_for

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "../Frontend")
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
PROJECTS_FILE = os.path.join(BASE_DIR, "projects.json")

os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(
    __name__,
    static_folder=FRONTEND_DIR,
    static_url_path=""
)

app.secret_key = "emxelux_secret_key_2025"

# --- Admin Credentials ---
ADMIN_USERNAME = "emxelux"
ADMIN_PASSWORD = "emmtech12"

# --- Helper Functions ---
def load_projects():
    if not os.path.exists(PROJECTS_FILE):
        return []
    with open(PROJECTS_FILE, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_projects(projects):
    with open(PROJECTS_FILE, "w", encoding="utf-8") as f:
        json.dump(projects, f, indent=2)

# --- Static Pages ---
@app.route("/")
def home():
    return send_from_directory(FRONTEND_DIR, "index.html")

@app.route("/projects.html")
def projects_page():
    return send_from_directory(FRONTEND_DIR, "projects.html")

@app.route("/admin_upload.html")
def admin_upload():
    if not session.get("logged_in"):
        return redirect(url_for("home"))
    return send_from_directory(FRONTEND_DIR, "admin_upload.html")

# --- Authentication Routes ---
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        session["logged_in"] = True
        return jsonify({"message": "Login successful!"})
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return jsonify({"message": "Logged out successfully"})

@app.route("/check_login")
def check_login():
    return jsonify({"logged_in": session.get("logged_in", False)})

# --- Project Management ---
@app.route("/get_projects")
def get_projects():
    return jsonify(load_projects())

@app.route("/upload_project", methods=["POST"])
def upload_project():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        name = request.form.get("name")
        report = request.form.get("report")
        zip_file = request.files.get("zip")
        image_file = request.files.get("image")

        if not all([name, report, zip_file, image_file]):
            return "Missing required fields", 400

        zip_path = os.path.join(UPLOAD_DIR, zip_file.filename)
        image_path = os.path.join(UPLOAD_DIR, image_file.filename)
        zip_file.save(zip_path)
        image_file.save(image_path)

        projects = load_projects()
        projects.append({
            "name": name,
            "report": report,
            "zip": zip_file.filename,
            "image": image_file.filename
        })
        save_projects(projects)
        return "Project uploaded successfully!", 200
    except Exception as e:
        print("UPLOAD ERROR:", e)
        return f"Error uploading project: {e}", 500

@app.route("/uploads/<path:filename>")
def download_file(filename):
    return send_from_directory(UPLOAD_DIR, filename, as_attachment=True)

@app.route("/delete_project/<int:project_id>", methods=["DELETE"])
def delete_project(project_id):
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401
    projects = load_projects()
    if project_id < 0 or project_id >= len(projects):
        return jsonify({'error': 'Invalid project ID'}), 404
    project = projects.pop(project_id)

    for file in [project.get("image"), project.get("zip")]:
        path = os.path.join(UPLOAD_DIR, file)
        if os.path.exists(path):
            os.remove(path)
    save_projects(projects)
    return jsonify({'message': 'Project deleted successfully!'})

if __name__ == "__main__":
    app.run(debug=True)
