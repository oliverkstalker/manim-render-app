from flask import Flask, request, send_file, jsonify
import subprocess
import uuid
import os
import re
import glob

app = Flask(__name__)

@app.route("/render", methods=["POST"])
def render_manim():
    data = request.get_json()
    user_code = data.get("code")

    if not user_code:
        return jsonify({"error": "No code provided"}), 400

    scene_id = uuid.uuid4().hex[:8]
    scene_name = extract_scene_name(user_code)
    if not scene_name:
        return jsonify({"error": "No Scene class found in code."}), 400

    code_file = f"/tmp/scene_{scene_id}.py"

    try:
        with open(code_file, "w") as f:
            f.write(user_code)

        cmd = [
            "manim", code_file,
            scene_name,
            "-qm",
            "-o", f"scene_{scene_id}.mp4",
            "--media_dir", "/tmp"
        ]
        # Force the command to run with /tmp as the working directory.
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60, cwd="/tmp")
        
        os.remove(code_file)  # Clean up the temp Python file

        if result.returncode != 0:
            return jsonify({
                "error": "Manim rendering failed",
                "details": result.stderr
            }), 500

        # The expected output path now is:
        output_path = f"/tmp/videos/scene_{scene_id}/720p30/scene_{scene_id}.mp4"
        if not os.path.exists(output_path):
            return jsonify({"error": f"Expected video not found at {output_path}"}), 500

        return send_file(output_path, mimetype="video/mp4")

    except subprocess.TimeoutExpired:
        return jsonify({"error": "Rendering timed out."}), 504
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def extract_scene_name(code: str) -> str:
    pattern = r'class\s+(\w+)\s*\((?:.*?)Scene\):'
    match = re.search(pattern, code)
    return match.group(1) if match else None

if __name__ == '__main__':
    app.run(debug=True)
