"""
MediVision AI — AI-Powered Medical Report Analyzer
Launch script: starts the Gradio application.
"""
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.main import initialize_app
from frontend.app import create_app, CUSTOM_CSS
from frontend.theme import get_theme


def main():
    """Initialize backend services and launch the Gradio UI."""
    print("=" * 60)
    print("  MediVision AI — AI-Powered Medical Report Analyzer")
    print("=" * 60)
    print()

    # Initialize backend (directories, DB, Ollama check)
    initialize_app()

    # Create and launch Gradio app
    app = create_app()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
        show_error=True,
        theme=get_theme(),
        css=CUSTOM_CSS,
    )


if __name__ == "__main__":
    main()
