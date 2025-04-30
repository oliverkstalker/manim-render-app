from flask import Flask, request, send_file, jsonify
import subprocess
import uuid
import os
import re
import traceback
import glob
from werkzeug.exceptions import BadRequest
import sys

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
            sys.executable, "-m", "manim",
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
            timeout=300,
            cwd=MEDIA_DIR
        )

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

        print("[DEBUG] Locating rendered .mp4...")
        candidate_paths = glob.glob(f"/tmp/media/videos/{scene_id}/**/*.mp4", recursive=True)
        if candidate_paths:
            output_path = candidate_paths[0]
            print(f"[SUCCESS] Video file found at: {output_path}")
        else:
            print("[ERROR] Could not find rendered video in any subdirectory.")
            os.system("find /tmp/videos -name '*.mp4'")
            return jsonify({
                "error": "Video not found",
                "searched": f"/tmp/videos/scene_{scene_id}/**/"
            }), 500

        try:
            return send_file(output_path, mimetype="video/mp4")
        except Exception as e:
            print("[SEND FILE ERROR]", str(e))
            return jsonify({"error": "Failed to send video", "details": str(e)}), 500

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
