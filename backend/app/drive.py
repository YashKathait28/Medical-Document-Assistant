from __future__ import annotations

import json
import io
from pathlib import Path
from typing import Dict, List

import gdown
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

from .config import GOOGLE_DRIVE_FOLDER_ID, GOOGLE_DRIVE_FOLDER_URL, GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON


def _folder_id_from_url(url: str) -> str:
    if "folders/" in url:
        return url.split("folders/")[1].split("?")[0]
    return ""


def download_public_folder(target_dir: Path) -> List[Dict[str, str]]:
    folder_url = GOOGLE_DRIVE_FOLDER_URL
    if not folder_url:
        return []
    target_dir.mkdir(parents=True, exist_ok=True)
    gdown.download_folder(url=folder_url, output=str(target_dir), quiet=True)
    files: List[Dict[str, str]] = []
    for path in target_dir.rglob("*"):
        if path.is_file():
            files.append({"path": str(path), "source_link": ""})
    return files


def download_with_service_account(target_dir: Path) -> List[Dict[str, str]]:
    if not GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON:
        return []
    credentials_info = json.loads(Path(GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON).read_text())
    credentials = service_account.Credentials.from_service_account_info(
        credentials_info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    service = build("drive", "v3", credentials=credentials)

    folder_id = GOOGLE_DRIVE_FOLDER_ID or _folder_id_from_url(GOOGLE_DRIVE_FOLDER_URL)
    if not folder_id:
        return []

    query = f"'{folder_id}' in parents and trashed = false"
    response = service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
    files = response.get("files", [])

    downloaded: List[Dict[str, str]] = []
    target_dir.mkdir(parents=True, exist_ok=True)
    for item in files:
        file_id = item["id"]
        name = item["name"]
        file_path = target_dir / name
        request = service.files().get_media(fileId=file_id)
        with io.BytesIO() as buffer:
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            file_path.write_bytes(buffer.getvalue())
        if file_path.exists():
            downloaded.append(
                {
                    "path": str(file_path),
                    "source_link": item.get("webViewLink", ""),
                }
            )
    return downloaded
