"""
MediVision AI — AI-Powered Medical Report Analyzer
Launch script: starts the Streamlit application.
"""
import os
import sys
import subprocess


def main():
    print("=" * 60)
    print("  MediVision AI — AI-Powered Medical Report Analyzer")
    print("=" * 60)
    print()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    app_script = os.path.join(project_dir, "streamlit_app.py")

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        app_script,
        "--server.port=8501",
        "--server.address=0.0.0.0",
        "--browser.gatherUsageStats=false",
    ]

    print("Launching MediVision AI Streamlit app on http://localhost:8501 ...")
    try:
        subprocess.run(cmd, cwd=project_dir)
    except KeyboardInterrupt:
        print("\nShutting down MediVision AI application.")


if __name__ == "__main__":
    main()
