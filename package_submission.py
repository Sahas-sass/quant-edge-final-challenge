"""
package_submission.py
Packages the Round 2 Final Challenge project into a clean ZIP file (under 25 MB).
"""

import os
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ZIP_NAME = "QuantEdge_Final_Submission.zip"
ZIP_PATH = os.path.join(BASE_DIR, ZIP_NAME)

INCLUDED_ITEMS = [
    "run_all.py",
    "requirements.txt",
    "README.md",
    ".gitignore",
    "data",
    "src",
    "output"
]

EXCLUDED_EXTS = [".pyc", ".git", ".DS_Store"]
EXCLUDED_DIRS = ["__pycache__", ".pytest_cache", ".idea", ".vscode"]


def create_submission_zip():
    print(f"[Packager] Creating final challenge submission archive: {ZIP_NAME}...")
    if os.path.exists(ZIP_PATH):
        os.remove(ZIP_PATH)

    with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in INCLUDED_ITEMS:
            item_path = os.path.join(BASE_DIR, item)
            if not os.path.exists(item_path):
                print(f"[Packager] Warning: {item} does not exist, skipping.")
                continue

            if os.path.isfile(item_path):
                zf.write(item_path, arcname=item)
                print(f"  -> Added file: {item}")
            elif os.path.isdir(item_path):
                for root, dirs, files in os.walk(item_path):
                    dirs[:] = [d for d in dirs if d not in EXCLUDED_DIRS]
                    for f in files:
                        if any(f.endswith(ext) for ext in EXCLUDED_EXTS):
                            continue
                        full_path = os.path.join(root, f)
                        rel_path = os.path.relpath(full_path, BASE_DIR)
                        zf.write(full_path, arcname=rel_path)
                print(f"  -> Added directory: {item}/")

    size_bytes = os.path.getsize(ZIP_PATH)
    size_mb = size_bytes / (1024 * 1024)
    print(f"\n[Packager] Final Archive successfully created!")
    print(f"  -> Path: {ZIP_PATH}")
    print(f"  -> Size: {size_mb:.2f} MB ({size_bytes} bytes)")
    if size_mb <= 25.0:
        print(f"  -> Compliance: PASS ({size_mb:.2f} MB <= 25.0 MB)")
    else:
        print(f"  -> Compliance: WARNING (Size exceeds 25 MB)")


if __name__ == "__main__":
    create_submission_zip()
