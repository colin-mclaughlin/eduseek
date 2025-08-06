#!/usr/bin/env python3
"""
Ingest downloaded files from the downloads/ directory into the FastAPI backend.

Usage:
  python ingest_downloaded_files.py --course-json <path-to-json> [--backend-url <url>] [--course-id <id>] [--course-name <name>]
  python ingest_downloaded_files.py --all [--backend-url <url>]

If --all is used, ingests all course JSONs in downloads/.

This script:
1. Reads the course JSON metadata
2. Uploads each file to the backend /upload endpoint
3. Includes course context (course_id, course_name, content_hash, scrape_batch_id) if available
4. Provides detailed feedback on success/failure/duplicates
5. Handles duplicates and missing files gracefully
6. Logs all ingestion attempts to ingestion_log.json
"""

import os
import sys
import requests
import json
from pathlib import Path
import argparse
import time
import hashlib
from datetime import datetime

# Defaults
DEFAULT_BACKEND_URL = "http://localhost:8000"
UPLOAD_ENDPOINT_PATH = "/api/upload"
DOWNLOADS_DIR = "downloads"
INGESTION_LOG = "ingestion_log.json"

def parse_args():
    parser = argparse.ArgumentParser(description="Ingest downloaded course files into backend.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--course-json', type=str, help='Path to course JSON metadata file')
    group.add_argument('--all', action='store_true', help='Ingest all course JSONs in downloads/')
    parser.add_argument('--backend-url', type=str, default=DEFAULT_BACKEND_URL, help='Backend base URL')
    parser.add_argument('--course-id', type=str, help='Override course ID (for single course)')
    parser.add_argument('--course-name', type=str, help='Override course name (for single course)')
    return parser.parse_args()

def get_course_json_files():
    """Return all course JSON metadata files in downloads/ directory."""
    return list(Path(DOWNLOADS_DIR).glob('course_files_from_zip_*.json'))

def extract_course_info_from_filename(json_path):
    """Extract course_id and course_name from the JSON filename."""
    name = Path(json_path).stem
    parts = name.split('_')
    # Format: course_files_from_zip_<course_id>_<course_name>
    if len(parts) >= 5:
        course_id = parts[4]
        course_name = '_'.join(parts[5:])
        return course_id, course_name
    return None, None

def compute_sha256(file_path):
    """Compute sha256 hash of a file."""
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def append_to_ingestion_log(log_entries):
    """Append a list of log entries to the persistent ingestion log JSON file."""
    if os.path.exists(INGESTION_LOG):
        with open(INGESTION_LOG, 'r', encoding='utf-8') as f:
            try:
                log = json.load(f)
            except Exception:
                log = []
    else:
        log = []
    log.extend(log_entries)
    with open(INGESTION_LOG, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

def upload_file(file_path, entry, upload_url, course_id=None, course_name=None, scrape_batch_id=None):
    """Upload a single file to the backend with course context and content_hash."""
    try:
        content_hash = compute_sha256(file_path)
        with open(file_path, 'rb') as f:
            files = {'file': (entry['filename'], f, 'application/octet-stream')}
            data = {
                'file_type': entry.get('file_type', ''),
                'content_hash': content_hash
            }
            if course_id:
                data['course_id'] = course_id
            if course_name:
                data['course_name'] = course_name
            if scrape_batch_id:
                data['scrape_batch_id'] = scrape_batch_id
            resp = requests.post(upload_url, files=files, data=data, timeout=120)
        if resp.status_code == 200:
            result = resp.json()
            print(f"  SUCCESS: Uploaded: {entry['filename']} → ID: {result.get('id', 'N/A')}")
            return 'uploaded', content_hash
        elif resp.status_code == 409:
            print(f"  SKIPPED: Skipped duplicate: {entry['filename']} (already exists on backend)")
            return 'duplicate', content_hash
        else:
            print(f"  ERROR: Failed: {entry['filename']} (HTTP {resp.status_code}): {resp.text}")
            return 'failed', content_hash
    except Exception as e:
        print(f"  💥 Error uploading {entry['filename']}: {e}")
        return 'failed', None

def ingest_course_json(json_path, backend_url, course_id_override=None, course_name_override=None, scrape_batch_id=None):
    print(f"\nLIST: Ingesting course JSON: {json_path}")
    upload_url = backend_url.rstrip('/') + UPLOAD_ENDPOINT_PATH
    with open(json_path, 'r', encoding='utf-8') as f:
        entries = json.load(f)
    course_id, course_name = extract_course_info_from_filename(json_path)
    if course_id_override:
        course_id = course_id_override
    if course_name_override:
        course_name = course_name_override
    print(f"   Course ID: {course_id}")
    print(f"   Course Name: {course_name}")
    uploaded, duplicate, failed, missing = 0, 0, 0, 0
    log_entries = []
    for entry in entries:
        file_path = os.path.join(DOWNLOADS_DIR, entry['path'])
        if not os.path.exists(file_path):
            print(f"  WARNING: Missing file: {file_path}")
            missing += 1
            log_entries.append({
                'filename': entry['filename'],
                'path': entry['path'],
                'course_id': course_id,
                'course_name': course_name,
                'scrape_batch_id': scrape_batch_id,
                'timestamp': datetime.now().isoformat(),
                'status': 'missing',
                'content_hash': None
            })
            continue
        result, content_hash = upload_file(file_path, entry, upload_url, course_id, course_name, scrape_batch_id)
        log_entries.append({
            'filename': entry['filename'],
            'path': entry['path'],
            'course_id': course_id,
            'course_name': course_name,
            'scrape_batch_id': scrape_batch_id,
            'timestamp': datetime.now().isoformat(),
            'status': result,
            'content_hash': content_hash
        })
        if result == 'uploaded':
            uploaded += 1
        elif result == 'duplicate':
            duplicate += 1
        else:
            failed += 1
        time.sleep(0.2)
    append_to_ingestion_log(log_entries)
    print(f"   SUCCESS: Uploaded: {uploaded} | SKIPPED: Duplicates: {duplicate} | ERROR: Failed: {failed} | WARNING: Missing: {missing}")
    return uploaded, duplicate, failed, missing

def main():
    args = parse_args()
    backend_url = args.backend_url
    scrape_batch_id = datetime.now().strftime('batch_%Y%m%d-%H%M%S')
    total_uploaded, total_duplicate, total_failed, total_missing = 0, 0, 0, 0
    if args.all:
        json_files = get_course_json_files()
        if not json_files:
            print(f"ERROR: No course JSON files found in {DOWNLOADS_DIR}/")
            sys.exit(1)
        for json_path in json_files:
            u, d, f, m = ingest_course_json(json_path, backend_url, scrape_batch_id=scrape_batch_id)
            total_uploaded += u
            total_duplicate += d
            total_failed += f
            total_missing += m
    else:
        if not os.path.exists(args.course_json):
            print(f"ERROR: Course JSON not found: {args.course_json}")
            sys.exit(1)
        u, d, f, m = ingest_course_json(
            args.course_json, backend_url, args.course_id, args.course_name, scrape_batch_id=scrape_batch_id
        )
        total_uploaded += u
        total_duplicate += d
        total_failed += f
        total_missing += m
    print("\n============================")
    print(f"🎉 Uploaded: {total_uploaded}")
    print(f"SKIPPED: Duplicates skipped: {total_duplicate}")
    print(f"ERROR: Failed: {total_failed}")
    print(f"WARNING: Missing: {total_missing}")
    print(f"📝 Ingestion log updated: {INGESTION_LOG}")
    print("============================\n")
    if total_failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main() 