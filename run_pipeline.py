"""Run the full pipeline: cleaning -> EDA -> training -> Word report."""
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).parent / "src"

for step in ["clean.py", "eda.py", "train.py", "export_lite.py", "build_docx.py"]:
    print(f"\n=== {step} ===")
    subprocess.run([sys.executable, step], cwd=SRC, check=True)
print("\nDone. Start the app with:  python app.py")
