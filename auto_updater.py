import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

from app_version import APP_VERSION


UPDATE_TIMEOUT_SECONDS = 30


def app_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def data_dir():
    return Path(os.environ.get("WEIGHMAN_DATA_DIR") or app_dir()).resolve()


def parse_version(value):
    parts = []
    for chunk in str(value or "0").replace("-", ".").split("."):
        number = "".join(char for char in chunk if char.isdigit())
        parts.append(int(number or 0))
    return tuple(parts or [0])


def is_newer_version(remote_version, current_version=APP_VERSION):
    remote_parts = parse_version(remote_version)
    current_parts = parse_version(current_version)
    max_length = max(len(remote_parts), len(current_parts))
    remote_parts += (0,) * (max_length - len(remote_parts))
    current_parts += (0,) * (max_length - len(current_parts))
    return remote_parts > current_parts


def fetch_json(url):
    request = urllib.request.Request(url, headers={"User-Agent": f"Weighman-WMS/{APP_VERSION}"})
    with urllib.request.urlopen(request, timeout=UPDATE_TIMEOUT_SECONDS) as response:
        return json.loads(response.read().decode("utf-8"))


def check_for_update(manifest_url):
    manifest_url = str(manifest_url or "").strip()
    if not manifest_url:
        return {
            "configured": False,
            "currentVersion": APP_VERSION,
            "updateAvailable": False,
            "message": "Update manifest URL is not configured.",
        }

    try:
        manifest = fetch_json(manifest_url)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {
            "configured": True,
            "currentVersion": APP_VERSION,
            "updateAvailable": False,
            "message": f"Unable to check for updates: {exc}",
        }

    remote_version = str(manifest.get("version") or "").strip()
    download_url = str(manifest.get("downloadUrl") or manifest.get("download_url") or "").strip()
    update_available = bool(remote_version and download_url and is_newer_version(remote_version))

    return {
        "configured": True,
        "currentVersion": APP_VERSION,
        "latestVersion": remote_version or APP_VERSION,
        "downloadUrl": download_url,
        "sha256": str(manifest.get("sha256") or "").strip(),
        "notes": str(manifest.get("notes") or "").strip(),
        "updateAvailable": update_available,
        "message": "Update available." if update_available else "Already up to date.",
        "manifest": manifest,
    }


def download_file(url, destination):
    request = urllib.request.Request(url, headers={"User-Agent": f"Weighman-WMS/{APP_VERSION}"})
    with urllib.request.urlopen(request, timeout=UPDATE_TIMEOUT_SECONDS) as response:
        with destination.open("wb") as file_handle:
            shutil.copyfileobj(response, file_handle)


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def update_root(extract_dir):
    entries = [entry for entry in Path(extract_dir).iterdir() if entry.name not in {"__MACOSX"}]
    if len(entries) == 1 and entries[0].is_dir():
        return entries[0]
    return Path(extract_dir)


def stage_update(update_info):
    download_url = update_info.get("downloadUrl")
    latest_version = update_info.get("latestVersion") or "latest"
    if not download_url:
        raise ValueError("Update download URL is missing.")

    updates_dir = data_dir() / "updates"
    updates_dir.mkdir(parents=True, exist_ok=True)
    zip_path = updates_dir / f"weighman-update-{latest_version}.zip"
    extract_dir = updates_dir / f"weighman-update-{latest_version}"

    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)

    download_file(download_url, zip_path)

    expected_sha = str(update_info.get("sha256") or "").strip().lower()
    if expected_sha:
        actual_sha = file_sha256(zip_path)
        if actual_sha.lower() != expected_sha:
            raise ValueError("Downloaded update checksum does not match.")

    with zipfile.ZipFile(zip_path, "r") as archive:
        archive.extractall(extract_dir)

    return update_root(extract_dir)


def write_windows_update_script(staged_dir):
    current_exe = Path(sys.executable).resolve()
    target_dir = current_exe.parent
    script_path = data_dir() / "updates" / "apply_update.bat"
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(
        "\n".join(
            [
                "@echo off",
                "setlocal",
                "timeout /t 2 /nobreak > nul",
                f'taskkill /pid {os.getpid()} /f > nul 2> nul',
                f'xcopy "{staged_dir}" "{target_dir}" /E /Y /I > nul',
                f'start "" "{current_exe}"',
                "endlocal",
            ]
        ),
        encoding="utf-8",
    )
    return script_path


def apply_update_and_restart(update_info):
    if not getattr(sys, "frozen", False):
        raise RuntimeError("Auto update apply is available only in the packaged .exe.")

    staged_dir = stage_update(update_info)
    script_path = write_windows_update_script(staged_dir)
    subprocess.Popen(
        ["cmd.exe", "/c", str(script_path)],
        cwd=str(data_dir()),
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )

    def exit_soon():
        time.sleep(0.8)
        os._exit(0)

    threading.Thread(target=exit_soon, daemon=True).start()
