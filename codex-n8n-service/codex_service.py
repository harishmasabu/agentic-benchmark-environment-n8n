from flask import Flask, request, jsonify
import subprocess
import os
import uuid
import threading

app = Flask(__name__)

CODEX_PATH = "/Users/harishmasabu/.local/bin/codex"

# ---------------------------------------------------------
# ASYNC JOB STORAGE
# ---------------------------------------------------------

# Stores background Codex jobs.
# This is in-memory storage, which is fine for the benchmark.
jobs = {}

# Protect jobs dictionary because multiple threads can access it.
jobs_lock = threading.Lock()


# ---------------------------------------------------------
# HELPER: BUILD CODEX COMMAND
# ---------------------------------------------------------

def build_codex_command(prompt, mode):

    if mode == "read":
        sandbox = "read-only"
    else:
        sandbox = "workspace-write"

    return [
        CODEX_PATH,
        "exec",
        "--skip-git-repo-check",
        "--sandbox",
        sandbox,
        prompt
    ]


# ---------------------------------------------------------
# EXISTING SYNCHRONOUS ENDPOINT
# ---------------------------------------------------------
#
# Keep this because:
# - Decision Agent can continue using it
# - Execution Agent can continue using it
# - Your first Workflow can continue using it
#
# ---------------------------------------------------------

@app.route("/run", methods=["POST"])
def run_codex():

    data = request.get_json()

    if not data or "prompt" not in data:
        return jsonify({
            "error": "No prompt provided"
        }), 400

    prompt = data["prompt"]
    workspace = data.get("workspace")
    mode = data.get("mode", "read")

    if workspace and not os.path.isdir(workspace):
        return jsonify({
            "success": False,
            "error": "Workspace does not exist",
            "received_workspace": repr(workspace)
        }), 400

    if mode not in ["read", "write"]:
        return jsonify({
            "success": False,
            "error": "Invalid mode. Use 'read' or 'write'."
        }), 400

    try:

        command = build_codex_command(prompt, mode)

        result = subprocess.run(
            command,
            cwd=workspace if workspace else None,
            capture_output=True,
            text=True,
            timeout=300
        )

        return jsonify({
            "success": result.returncode == 0,
            "output": result.stdout,
            "codex_logs": result.stderr,
            "exit_code": result.returncode,
            "workspace": workspace,
            "mode": mode
        })

    except subprocess.TimeoutExpired:

        return jsonify({
            "success": False,
            "error": "Codex execution timed out"
        }), 500

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


# =========================================================
# ASYNCHRONOUS CODEX JOBS
# =========================================================


# ---------------------------------------------------------
# BACKGROUND WORKER
# ---------------------------------------------------------

def run_codex_job(job_id, prompt, workspace, mode):

    # Mark job as running
    with jobs_lock:
        jobs[job_id]["status"] = "running"

    try:

        command = build_codex_command(prompt, mode)

        result = subprocess.run(
            command,
            cwd=workspace if workspace else None,
            capture_output=True,
            text=True,
            timeout=300
        )

        with jobs_lock:

            jobs[job_id].update({
                "status": (
                    "completed"
                    if result.returncode == 0
                    else "failed"
                ),
                "success": result.returncode == 0,
                "output": result.stdout,
                "codex_logs": result.stderr,
                "exit_code": result.returncode
            })

    except subprocess.TimeoutExpired:

        with jobs_lock:

            jobs[job_id].update({
                "status": "failed",
                "success": False,
                "error": "Codex execution timed out"
            })

    except Exception as e:

        with jobs_lock:

            jobs[job_id].update({
                "status": "failed",
                "success": False,
                "error": str(e)
            })


# ---------------------------------------------------------
# CREATE ASYNC JOB
# ---------------------------------------------------------
#
# POST /jobs
#
# Starts Codex in the background and immediately returns
# a job_id instead of waiting for Codex to finish.
#
# ---------------------------------------------------------

@app.route("/jobs", methods=["POST"])
def create_job():

    data = request.get_json()

    if not data or "prompt" not in data:

        return jsonify({
            "success": False,
            "error": "No prompt provided"
        }), 400

    prompt = data["prompt"]
    workspace = data.get("workspace")
    mode = data.get("mode", "read")

    if workspace and not os.path.isdir(workspace):

        return jsonify({
            "success": False,
            "error": "Workspace does not exist",
            "received_workspace": repr(workspace)
        }), 400

    if mode not in ["read", "write"]:

        return jsonify({
            "success": False,
            "error": "Invalid mode. Use 'read' or 'write'."
        }), 400

    # Generate unique job ID
    job_id = str(uuid.uuid4())

    # Store initial job information
    with jobs_lock:

        jobs[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "workspace": workspace,
            "mode": mode
        }

    # Start Codex in a background thread
    thread = threading.Thread(
        target=run_codex_job,
        args=(
            job_id,
            prompt,
            workspace,
            mode
        ),
        daemon=True
    )

    thread.start()

    # IMPORTANT:
    # We do NOT wait for Codex here.
    # n8n receives the job ID immediately.

    return jsonify({
        "success": True,
        "job_id": job_id,
        "status": "queued",
        "workspace": workspace,
        "mode": mode
    }), 202


# ---------------------------------------------------------
# CHECK ASYNC JOB
# ---------------------------------------------------------
#
# GET /jobs/<job_id>
#
# n8n calls this later to check whether the job finished.
#
# ---------------------------------------------------------

@app.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id):

    with jobs_lock:

        job = jobs.get(job_id)

        if not job:

            return jsonify({
                "success": False,
                "error": "Job not found",
                "job_id": job_id
            }), 404

        # Return a copy so the dictionary isn't modified
        # while Flask is serializing it.
        response = dict(job)

    return jsonify(response)


# ---------------------------------------------------------
# OPTIONAL: LIST ALL JOBS
# ---------------------------------------------------------
#
# Useful while demonstrating/debugging.
#
# GET /jobs
#
# ---------------------------------------------------------

@app.route("/jobs", methods=["GET"])
def list_jobs():

    with jobs_lock:

        all_jobs = [
            dict(job)
            for job in jobs.values()
        ]

    return jsonify({
        "count": len(all_jobs),
        "jobs": all_jobs
    })


# =========================================================
# INDEPENDENT VERIFIER
# =========================================================

@app.route("/verify", methods=["POST"])
def verify():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "error": "No request body provided"
        }), 400

    workspace = data.get("workspace")

    if not workspace or not os.path.isdir(workspace):

        return jsonify({
            "success": False,
            "error": "Invalid workspace"
        }), 400

    try:

        result = subprocess.run(
            ["python3", "verifier.py"],
            cwd=workspace,
            capture_output=True,
            text=True,
            timeout=120
        )

        # -------------------------------------------------
        # IMPORTANT FIX
        #
        # Workflow verifier:
        # BENCHMARK_RESULT=PASS
        #
        # WorkGraph verifier:
        # WORKGRAPH_RESULT=PASS
        #
        # Support both.
        # -------------------------------------------------

        workflow_passed = (
            "BENCHMARK_RESULT=PASS"
            in result.stdout
        )

        workgraph_passed = (
            "WORKGRAPH_RESULT=PASS"
            in result.stdout
        )

        passed = (
            result.returncode == 0
            and (
                workflow_passed
                or workgraph_passed
            )
        )

        return jsonify({
            "success": True,
            "benchmark_passed": passed,
            "output": result.stdout,
            "verifier_logs": result.stderr,
            "exit_code": result.returncode,
            "workspace": workspace
        })

    except subprocess.TimeoutExpired:

        return jsonify({
            "success": False,
            "benchmark_passed": False,
            "error": "Verifier timed out"
        }), 500

    except Exception as e:

        return jsonify({
            "success": False,
            "benchmark_passed": False,
            "error": str(e)
        }), 500


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    app.run(
        host="127.0.0.1",
        port=5001,
        threaded=True
    )