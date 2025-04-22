from flask import Flask, request, send_file, jsonify
import subprocess
import uuid
import os
import re
import traceback
from werkzeug.exceptions import BadRequest

app = Flask(__name__)

MEDIA_DIR = "/tmp"
RESOLUTION = "720p30"

@app.route("/render", methods=["POST"])
def render_manim():
    print("[DEBUG] Received request to /render")
    try:
        data = request.get_json(force=True)
        print("[DEBUG] JSON parsed successfully!")
        user_code = data.get("code")
        print("==== [REQUEST RECEIVED] ====")
        print(user_code)
        print("=============================")

        if not user_code:
            return jsonify({"error": "No code provided"}), 400

        scene_id = uuid.uuid4().hex[:8]
        scene_name = extract_scene_name(user_code)

        if not scene_name:
            print("[ERROR] Could not extract Scene class.")
            return jsonify({"error": "No Scene class found in code."}), 400

        print(f"[INFO] Scene name extracted: {scene_name}")

        code_path = os.path.join(MEDIA_DIR, f"scene_{scene_id}.py")
        with open(code_path, "w") as f:
            f.write(user_code)

        output_name = f"scene_{scene_id}.mp4"
        cmd = [
            "manim",
            code_path,
            scene_name,
            "-qm",
            "-o", output_name,
            "--media_dir", MEDIA_DIR
        ]

        print(f"[INFO] Running command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=90,
            cwd=MEDIA_DIR
        )

        # Remove the temp Python file
        os.remove(code_path)

        print("==== [STDOUT] ====")
        print(result.stdout)
        print("==== [STDERR] ====")
        print(result.stderr)

        if result.returncode != 0:
            return jsonify({
                "error": "Manim rendering failed",
                "details": result.stderr.strip(),
                "stdout": result.stdout.strip()
            }), 500

        # Construct the expected video output path
        output_path = os.path.join(MEDIA_DIR, "videos", f"scene_{scene_id}", RESOLUTION, output_name)

        if not os.path.exists(output_path):
            print(f"[ERROR] Output file missing: {output_path}")
            parent = os.path.dirname(output_path)
            if os.path.exists(parent):
                print(f"[INFO] Directory contents of {parent}: {os.listdir(parent)}")
            else:
                print(f"[INFO] Parent directory {parent} does not exist.")
            return jsonify({
                "error": f"Expected video not found at {output_path}",
                "dir_contents": os.listdir(os.path.dirname(parent)) if os.path.exists(os.path.dirname(parent)) else "N/A"
            }), 500

        print(f"[SUCCESS] Video file created at: {output_path}")
        return send_file(output_path, mimetype="video/mp4")

    except subprocess.TimeoutExpired:
        print("[ERROR] Manim process timed out.")
        return jsonify({"error": "Rendering timed out."}), 504

    except Exception as e:
        print("[EXCEPTION] Unexpected error occurred:")
        traceback.print_exc()
        return jsonify({"error": str(e), "traceback": traceback.format_exc()}), 500


def extract_scene_name(code: str) -> str:
    pattern = r'class\s+(\w+)\s*\((?:.*?)Scene\):'
    match = re.search(pattern, code)
    return match.group(1) if match else None

@app.errorhandler(BadRequest)
def handle_bad_request(e):
    print("[GLOBAL] BadRequest exception triggered.")
    print(e)
    return jsonify({"error": "Invalid JSON or malformed payload", "message": str(e)}), 400



if __name__ == '__main__':
    app.run(debug=True)
