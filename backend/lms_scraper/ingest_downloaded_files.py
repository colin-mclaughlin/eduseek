#!/usr/bin/env python3
"""
Ingest downloaded files from the downloads/ directory into the FastAPI backend.

This script:
1. Scans the downloads/ directory for files
2. Uploads each file to the backend /upload endpoint
3. Provides detailed feedback on success/failure
4. Handles duplicates gracefully
"""

import os
import sys
import requests
import json
from pathlib import Path
from typing import List, Dict, Optional
import time

# Configuration
BACKEND_URL = "http://localhost:8000"
UPLOAD_ENDPOINT = f"{BACKEND_URL}/api/files/upload"
DOWNLOADS_DIR = "downloads"

def check_backend_health() -> bool:
    """Check if the backend is running and healthy."""
    try:
        response = requests.get(f"{BACKEND_URL}/docs", timeout=5)
        return response.status_code == 200
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend not accessible: {e}")
        return False

def get_downloaded_files() -> List[Path]:
    """Get all files from the downloads directory."""
    downloads_path = Path(DOWNLOADS_DIR)
    
    if not downloads_path.exists():
        print(f"❌ Downloads directory '{DOWNLOADS_DIR}' not found")
        return []
    
    files = []
    for file_path in downloads_path.iterdir():
        if file_path.is_file():
            files.append(file_path)
    
    return sorted(files)

def upload_file(file_path: Path) -> Dict:
    """Upload a single file to the backend."""
    try:
        print(f"📤 Uploading: {file_path.name}")
        
        # Open file in binary mode
        with open(file_path, 'rb') as f:
            files = {'file': (file_path.name, f, 'application/octet-stream')}
            
            # Upload to backend
            response = requests.post(
                UPLOAD_ENDPOINT,
                files=files,
                timeout=30  # 30 second timeout for uploads
            )
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ Success: {file_path.name} → ID: {result.get('id', 'N/A')}")
            return {
                'success': True,
                'filename': file_path.name,
                'file_id': result.get('id'),
                'error': None
            }
        else:
            error_msg = f"HTTP {response.status_code}: {response.text}"
            print(f"  ❌ Failed: {file_path.name} → {error_msg}")
            return {
                'success': False,
                'filename': file_path.name,
                'file_id': None,
                'error': error_msg
            }
            
    except requests.exceptions.Timeout:
        error_msg = "Upload timeout (30s)"
        print(f"  ⏰ Timeout: {file_path.name} → {error_msg}")
        return {
            'success': False,
            'filename': file_path.name,
            'file_id': None,
            'error': error_msg
        }
    except requests.exceptions.RequestException as e:
        error_msg = f"Network error: {e}"
        print(f"  🌐 Network error: {file_path.name} → {error_msg}")
        return {
            'success': False,
            'filename': file_path.name,
            'file_id': None,
            'error': error_msg
        }
    except Exception as e:
        error_msg = f"Unexpected error: {e}"
        print(f"  💥 Error: {file_path.name} → {error_msg}")
        return {
            'success': False,
            'filename': file_path.name,
            'file_id': None,
            'error': error_msg
        }

def check_existing_files() -> List[str]:
    """Check which files already exist in the backend."""
    try:
        response = requests.get(f"{BACKEND_URL}/api/files/", timeout=10)
        if response.status_code == 200:
            files = response.json()
            return [file['filename'] for file in files]
        else:
            print(f"⚠️ Could not check existing files: HTTP {response.status_code}")
            return []
    except Exception as e:
        print(f"⚠️ Could not check existing files: {e}")
        return []

def main():
    """Main ingestion function."""
    print("🚀 Starting file ingestion process...")
    print(f"📁 Backend URL: {BACKEND_URL}")
    print(f"📂 Downloads directory: {DOWNLOADS_DIR}")
    print()
    
    # Check if backend is running
    if not check_backend_health():
        print("❌ Backend is not accessible. Please ensure the FastAPI server is running at http://localhost:8000")
        sys.exit(1)
    
    print("✅ Backend is accessible")
    
    # Get list of downloaded files
    files = get_downloaded_files()
    if not files:
        print("❌ No files found in downloads directory")
        sys.exit(1)
    
    print(f"📋 Found {len(files)} files to process")
    
    # Check for existing files (optional - for duplicate detection)
    existing_files = check_existing_files()
    if existing_files:
        print(f"📊 Found {len(existing_files)} existing files in backend")
    
    # Process each file
    results = []
    successful_uploads = 0
    failed_uploads = 0
    skipped_duplicates = 0
    
    for i, file_path in enumerate(files, 1):
        print(f"\n[{i}/{len(files)}] Processing: {file_path.name}")
        
        # Check for duplicates (optional)
        if file_path.name in existing_files:
            print(f"  ⏭️ Skipping duplicate: {file_path.name} (already exists)")
            skipped_duplicates += 1
            results.append({
                'success': False,
                'filename': file_path.name,
                'file_id': None,
                'error': 'Duplicate file'
            })
            continue
        
        # Upload the file
        result = upload_file(file_path)
        results.append(result)
        
        if result['success']:
            successful_uploads += 1
        else:
            failed_uploads += 1
        
        # Small delay to be respectful to the server
        time.sleep(0.5)
    
    # Print summary
    print("\n" + "="*50)
    print("📊 INGESTION SUMMARY")
    print("="*50)
    print(f"✅ Successful uploads: {successful_uploads}")
    print(f"❌ Failed uploads: {failed_uploads}")
    print(f"⏭️ Skipped duplicates: {skipped_duplicates}")
    print(f"📁 Total files processed: {len(files)}")
    
    if successful_uploads > 0:
        print(f"\n🎉 Successfully ingested {successful_uploads} files!")
    
    if failed_uploads > 0:
        print(f"\n⚠️ {failed_uploads} files failed to upload:")
        for result in results:
            if not result['success'] and result['error'] != 'Duplicate file':
                print(f"   • {result['filename']}: {result['error']}")
    
    # Save results to JSON file
    results_file = "ingestion_results.json"
    with open(results_file, 'w') as f:
        json.dump({
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'backend_url': BACKEND_URL,
            'downloads_dir': DOWNLOADS_DIR,
            'summary': {
                'total_files': len(files),
                'successful_uploads': successful_uploads,
                'failed_uploads': failed_uploads,
                'skipped_duplicates': skipped_duplicates
            },
            'results': results
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    
    # Exit with appropriate code
    if failed_uploads > 0:
        print("\n⚠️ Some files failed to upload. Check the results above.")
        sys.exit(1)
    else:
        print("\n✅ All files processed successfully!")
        sys.exit(0)

if __name__ == "__main__":
    main() 