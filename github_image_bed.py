#!/usr/bin/env python3
"""
GitHub + jsDelivr CDN Image Bed Service
Upload images to GitHub repository and return CDN URLs.
"""

import os
import sys
import base64
import hashlib
import time
from pathlib import Path
from datetime import datetime

import httpx

# Configuration
GITHUB_REPO = "Frank2T/image-bed"
GITHUB_BRANCH = "main"
GITHUB_API_BASE = "https://api.github.com"
JSDELIVR_BASE = f"https://cdn.jsdelivr.net/gh/{GITHUB_REPO}@{GITHUB_BRANCH}"

# Image storage paths
IMAGES_DIR = "images"
TEMP_DIR = "temp"


def get_github_token() -> str:
    """Get GitHub token from environment or gh CLI."""
    # Try environment variable first
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return token

    # Try gh CLI
    try:
        import subprocess
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except Exception as e:
        print(f"Error getting GitHub token: {e}", file=sys.stderr)
        print("Please set GITHUB_TOKEN environment variable or login with: gh auth login", file=sys.stderr)
        sys.exit(1)


def generate_filename(original_filename: str, use_temp: bool = False) -> str:
    """Generate unique filename with timestamp and hash."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Generate short hash from original filename
    file_hash = hashlib.md5(original_filename.encode()).hexdigest()[:8]
    ext = Path(original_filename).suffix or ".png"

    if use_temp:
        return f"{TEMP_DIR}/{timestamp}_{file_hash}{ext}"
    else:
        # Organize by date
        date_str = datetime.now().strftime("%Y/%m")
        return f"{IMAGES_DIR}/{date_str}/{timestamp}_{file_hash}{ext}"


def upload_to_github(file_path: str, github_path: str, token: str) -> bool:
    """Upload file to GitHub repository."""
    with open(file_path, "rb") as f:
        content = f.read()

    content_base64 = base64.b64encode(content).decode("utf-8")

    # Create or update file via GitHub API
    url = f"{GITHUB_API_BASE}/repos/{GITHUB_REPO}/contents/{github_path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Check if file exists (for update)
    data = {
        "message": f"Upload image: {Path(file_path).name}",
        "content": content_base64,
        "branch": GITHUB_BRANCH,
    }

    with httpx.Client(timeout=60.0) as client:
        # First check if file exists
        resp = client.get(url, headers=headers, params={"ref": GITHUB_BRANCH})
        if resp.status_code == 200:
            # File exists, need to include SHA for update
            existing = resp.json()
            data["sha"] = existing["sha"]

        # Upload/Update file
        resp = client.put(url, headers=headers, json=data)

        if resp.status_code in [200, 201]:
            print(f"✓ Uploaded to GitHub: {github_path}", file=sys.stderr)
            return True
        else:
            print(f"✗ GitHub upload failed: {resp.status_code} - {resp.text[:200]}", file=sys.stderr)
            return False


def get_cdn_url(github_path: str) -> str:
    """Get jsDelivr CDN URL for the uploaded file."""
    return f"{JSDELIVR_BASE}/{github_path}"


def upload_image(file_path: str, use_temp: bool = False) -> dict:
    """
    Upload image to GitHub + jsDelivr CDN.

    Args:
        file_path: Local path to image file
        use_temp: If True, store in temp directory (auto-cleanup)

    Returns:
        dict with keys: cdn_url, github_path, success, error
    """
    if not os.path.exists(file_path):
        return {"success": False, "error": f"File not found: {file_path}"}

    try:
        # Get GitHub token
        token = get_github_token()

        # Generate unique filename
        original_name = Path(file_path).name
        github_path = generate_filename(original_name, use_temp)

        # Upload to GitHub
        success = upload_to_github(file_path, github_path, token)

        if success:
            cdn_url = get_cdn_url(github_path)
            return {
                "success": True,
                "cdn_url": cdn_url,
                "github_path": github_path,
            }
        else:
            return {"success": False, "error": "GitHub upload failed"}

    except Exception as e:
        return {"success": False, "error": str(e)}


def upload_image_base64(image_base64: str, filename: str = "image.png", use_temp: bool = False) -> dict:
    """
    Upload base64-encoded image to GitHub + jsDelivr CDN.

    Args:
        image_base64: Base64-encoded image data
        filename: Original filename (for extension)
        use_temp: If True, store in temp directory

    Returns:
        dict with keys: cdn_url, github_path, success, error
    """
    try:
        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_base64)

        # Create temp file
        temp_dir = Path("temp_uploads")
        temp_dir.mkdir(exist_ok=True)
        temp_file = temp_dir / filename
        temp_file.write_bytes(image_bytes)

        # Upload using file method
        result = upload_image(str(temp_file), use_temp)

        # Cleanup temp file
        temp_file.unlink(missing_ok=True)

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}


def cleanup_temp_files(max_age_hours: int = 24):
    """Clean up old temp files (run periodically)."""
    # This would need to be implemented with GitHub API
    # For now, just print reminder
    print(f"Note: Temp files older than {max_age_hours}h should be cleaned up", file=sys.stderr)
    print(f"Consider running this periodically or using GitHub Actions", file=sys.stderr)


def main():
    """CLI interface."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python github_image_bed.py upload <file_path> [--temp]")
        print("  python github_image_bed.py upload-base64 <base64_string> [filename] [--temp]")
        print("  python github_image_bed.py cleanup")
        sys.exit(1)

    command = sys.argv[1]

    if command == "upload":
        if len(sys.argv) < 3:
            print("Error: file_path required", file=sys.stderr)
            sys.exit(1)

        file_path = sys.argv[2]
        use_temp = "--temp" in sys.argv

        result = upload_image(file_path, use_temp)

        # Output result as JSON
        import json
        print(json.dumps(result, indent=2))

        if result["success"]:
            print(f"\n✓ CDN URL: {result['cdn_url']}", file=sys.stderr)
        else:
            print(f"\n✗ Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

    elif command == "upload-base64":
        if len(sys.argv) < 3:
            print("Error: base64_string required", file=sys.stderr)
            sys.exit(1)

        base64_str = sys.argv[2]
        filename = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("--") else "image.png"
        use_temp = "--temp" in sys.argv

        result = upload_image_base64(base64_str, filename, use_temp)

        # Output result as JSON
        import json
        print(json.dumps(result, indent=2))

        if result["success"]:
            print(f"\n✓ CDN URL: {result['cdn_url']}", file=sys.stderr)
        else:
            print(f"\n✗ Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

    elif command == "cleanup":
        cleanup_temp_files()

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
