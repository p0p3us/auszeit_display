from flask import Flask, jsonify, send_from_directory, redirect, url_for, render_template, request
from pathlib import Path
from datetime import datetime

from modules.display_state import get_active_page, set_active_page
from modules.page_manager import list_html_pages, page_exists
from modules.settings import DEFAULT_PAGE, PAGES_DIR, RESOURCES_DIR, STATIC_DIR, UPLOAD_DIR
from modules.system_status import get_system_status

app = Flask(__name__)


@app.route("/")
def index():
    return redirect(url_for("admin"))


@app.route("/admin")
def admin():
    pages = list_html_pages()
    active_page = get_active_page()
    system_status = get_system_status()

    return render_template(
        "admin.html",
        pages=pages,
        active_page=active_page,
        system_status=system_status
    )

@app.route("/admin/upload", methods=["GET"])
def upload_form():
    return render_template("upload.html")


@app.route("/admin/upload", methods=["POST"])
def upload_file():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    uploaded_file = request.files.get("file")

    if uploaded_file is None or uploaded_file.filename == "":
        return jsonify({
            "status": "error",
            "message": "Keine Datei ausgewählt."
        }), 400

    filename = uploaded_file.filename

    if not filename.lower().endswith(".html"):
        return jsonify({
            "status": "error",
            "message": "Nur HTML-Dateien sind erlaubt."
        }), 400

    safe_filename = Path(filename).name
    target_path = UPLOAD_DIR / safe_filename

    uploaded_file.save(target_path)

    return redirect(url_for("admin"))

@app.route("/admin/set/<path:page_path>")
def set_display_page(page_path):
    if not page_exists(page_path):
        return jsonify({
            "status": "error",
            "message": "Page not found",
            "page": page_path
        }), 404

    set_active_page(page_path)
    return redirect(url_for("admin"))

@app.route("/admin/delete/<path:page_path>", methods=["POST"])
def delete_page(page_path):
    if not page_exists(page_path):
        return jsonify({
            "status": "error",
            "message": "Page not found",
            "page": page_path
        }), 404

    # Nur Upload-Seiten dürfen über die Oberfläche gelöscht werden.
    if not page_path.startswith("upload/"):
        return jsonify({
            "status": "error",
            "message": "Only upload pages can be deleted.",
            "page": page_path
        }), 403

    target_path = PAGES_DIR / page_path

    try:
        target_path.unlink()
    except OSError as error:
        return jsonify({
            "status": "error",
            "message": str(error),
            "page": page_path
        }), 500

    if get_active_page() == page_path:
        set_active_page(DEFAULT_PAGE)

    return redirect(url_for("admin"))

@app.route("/status")
def status():
    system_status = get_system_status()
    system_status.update({
        "system": "auszeit_display",
        "status": "running",
        "boot": "ssd",
        "active_page": get_active_page(),
    })

    return jsonify(system_status)


@app.route("/display")
def display():
    active_page = get_active_page()

    return render_template(
        "display.html",
        active_page=active_page,
        cache_buster=int(datetime.now().timestamp())
    )


@app.route("/pages/<path:filename>")
def serve_page(filename):
    return send_from_directory(PAGES_DIR, filename)

@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/resources/<path:filename>")
def resources(filename):
    return send_from_directory(RESOURCES_DIR, filename)

@app.route("/auszeit-display/resources/<path:filename>")
def serve_public_resources(filename):
    return send_from_directory(RESOURCES_DIR, filename)

@app.route("/auszeit-display/static/<path:filename>")
def serve_public_static(filename):
    return send_from_directory(STATIC_DIR, filename)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
