import subprocess
import sys
import os
import shutil

def run_command(command):
    print(f"Running: {' '.join(command)}")
    try:
        subprocess.run(command, check=True, capture_output=False)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}", file=sys.stderr)
        return False

def main():
    print("=== Setting up Federer Company Discovery Engine ===")
    
    # 1. Install dependencies from requirements.txt
    print("\n1. Installing pip dependencies...")
    requirements_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
    if not os.path.exists(requirements_file):
        print(f"Error: requirements.txt not found at {requirements_file}", file=sys.stderr)
        sys.exit(1)
        
    if not run_command([sys.executable, "-m", "pip", "install", "-r", requirements_file]):
        print("Failed to install requirements. Proceeding anyway...", file=sys.stderr)

    # 2. Install Playwright browser binaries
    print("\n2. Installing Playwright Chromium browser...")
    try:
        import playwright
        if not run_command([sys.executable, "-m", "playwright", "install", "chromium"]):
            print("Playwright browser installation failed. You might need to run 'playwright install chromium' manually.", file=sys.stderr)
    except ImportError:
        print("Playwright is not imported. Please run 'pip install playwright' and then 'playwright install chromium' manually.", file=sys.stderr)

    # 3. Local Ollama Model Setup (Optional Fallback Check)
    print("\n3. Checking local Ollama installation...")
    ollama_path = shutil.which("ollama")
    if ollama_path:
        print(f"Ollama detected at: {ollama_path}")
        print("Attempting to pull the default model 'qwen3:8b'...")
        try:
            # Run pull command
            result = subprocess.run(["ollama", "pull", "qwen3:8b"], capture_output=False)
            if result.returncode == 0:
                print("SUCCESS: Local model 'qwen3:8b' is pulled and ready.")
            else:
                print("\n[WARNING] Ollama is installed but pulling 'qwen3:8b' failed.")
                print("Make sure the Ollama desktop application is running (or run 'ollama serve' in another window) and execute:")
                print("ollama pull qwen3:8b")
        except Exception as e:
            print(f"[WARNING] Error contacting Ollama service: {e}")
            print("To run local models, start Ollama and run: ollama pull qwen3:8b")
    else:
        print("Ollama is not detected on your system PATH.")
        print("If you plan to use local offline models, install Ollama from https://ollama.com/ and pull the default model:")
        print("  ollama pull qwen3:8b")

    print("\n=== Setup Complete! ===")
    print("To run the application:")
    print("streamlit run app.py")

if __name__ == "__main__":
    main()
