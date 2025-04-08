from flask import Flask, request, send_file, jsonify
import subprocess
import uuid
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

job_queue = {}
job_results = {}
executor = ThreadPoolExecutor(max_workers=1)  # One job at a time

@app.route("/render", methods=["POST"])
def enqueue_render():
    data = request.get_json()
    user_code = data.get("code")

    if not user_code:
        return jsonify({"error": "No code provided"}), 400

    scene_name = extract_scene_name(user_code)
    if not scene_name:
        return jsonify({"error": "No Scene class found in code."}), 400

    job_id = uuid.uuid4().hex[:8]
    job_queue[job_id] = {
        "status": "pending",
        "scene_name": scene_name,
        "code": user_code
    }

    executor.submit(process_render_job, job_id)
    return jsonify({"job_id": job_id}), 202

@app.route("/status/<job_id>", methods=["GET"])
def check_status(job_id):
    if job_id not in job_queue:
        return jsonify({"error": "Invalid job ID"}), 404
    return jsonify({
        "status": job_queue[job_id]["status"]
    })

@app.route("/result/<job_id>", methods=["GET"])
def get_result(job_id):
    job = job_queue.get(job_id)
    if not job:
        return jsonify({"error": "Invalid job ID"}), 404
    if job["status"] != "done":
        return jsonify({"error": "Job not finished"}), 409

    output_path = job_results.get(job_id)
    if not output_path or not os.path.exists(output_path):
        return jsonify({"error": "Result file not found"}), 500

    return send_file(output_path, mimetype="video/mp4")

def process_render_job(job_id):
    job = job_queue[job_id]
    job["status"] = "running"

    scene_name = job["scene_name"]
    user_code = job["code"]
    code_file = f"/tmp/scene_{job_id}.py"
    output_video = f"scene_{job_id}.mp4"
    final_path = f"/tmp/videos/scene_{job_id}/720p30/{output_video}"

    try:
        with open(code_file, "w") as f:
            f.write(user_code)

        cmd = [
            "manim", code_file,
            scene_name,
            "-qm",
            "-o", output_video,
            "--media_dir", "/tmp"
        ]

        start_time = time.time()
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=90,
            cwd="/tmp"
        )
        os.remove(code_file)

        if result.returncode != 0:
            job["status"] = "error"
            job["error"] = result.stderr
            return

        if not os.path.exists(final_path):
            job["status"] = "error"
            job["error"] = "Video file not generated."
            return

        job_results[job_id] = final_path
        job["status"] = "done"

    except subprocess.TimeoutExpired:
        job["status"] = "error"
        job["error"] = "Rendering timed out."
    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)

def extract_scene_name(code: str) -> str:
    pattern = r'class\s+(\w+)\s*\((?:.*?)Scene\):'
    match = re.search(pattern, code)
    return match.group(1) if match else None

if __name__ == '__main__':
    app.run(debug=True)
