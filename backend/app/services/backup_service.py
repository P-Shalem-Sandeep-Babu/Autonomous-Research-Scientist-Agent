import os
import glob
import gzip
import shutil
import sqlite3
import hashlib
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger("arsa.backup")

class BackupService:
    def __init__(self, backup_dir: Optional[str] = None):
        self.backup_dir = os.path.abspath(backup_dir or settings.BACKUP_DIR)
        os.makedirs(self.backup_dir, exist_ok=True)

    def _get_sqlite_db_path(self) -> str:
        """Extracts the local file path from DATABASE_URL."""
        db_url = settings.DATABASE_URL
        if db_url.startswith("sqlite:///"):
            path = db_url.replace("sqlite:///", "")
            return os.path.abspath(path)
        raise ValueError(f"Automated SQLite backup is only supported for sqlite URLs, got: {db_url}")

    def _calculate_sha256(self, filepath: str) -> str:
        """Computes SHA-256 integrity checksum for a file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def create_backup(self, label: str = "manual") -> Dict[str, Any]:
        """
        Creates an atomic online snapshot of SQLite database using sqlite3.Connection.backup(),
        compresses it with gzip, verifies SHA-256 checksum, and manages retention.
        """
        db_path = self._get_sqlite_db_path()
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file not found at: {db_path}")

        timestamp_str = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        clean_label = "".join(c for c in label if c.isalnum() or c in "-_")
        snapshot_name = f"backup_{timestamp_str}_{clean_label}.db"
        temp_snapshot_path = os.path.join(self.backup_dir, snapshot_name)
        archive_name = f"{snapshot_name}.gz"
        archive_path = os.path.join(self.backup_dir, archive_name)

        logger.info(f"Starting atomic database backup: {db_path} -> {archive_path}")

        # 1. Atomic Online SQLite Backup (safe during concurrent live reads and writes)
        source_conn = sqlite3.connect(db_path)
        dest_conn = sqlite3.connect(temp_snapshot_path)
        try:
            source_conn.backup(dest_conn, pages=100)
            dest_conn.close()
            source_conn.close()
        except Exception as e:
            if os.path.exists(temp_snapshot_path):
                os.remove(temp_snapshot_path)
            source_conn.close()
            logger.error(f"Failed to perform online SQLite backup: {e}")
            raise e

        # 2. Gzip compression
        try:
            with open(temp_snapshot_path, "rb") as f_in:
                with gzip.open(archive_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
        finally:
            if os.path.exists(temp_snapshot_path):
                os.remove(temp_snapshot_path)

        # 3. Cryptographic integrity checksum
        sha256_checksum = self._calculate_sha256(archive_path)
        size_bytes = os.path.getsize(archive_path)

        # 4. Cloud Object Storage Sync (S3 / GCS hook)
        cloud_synced = self._sync_to_cloud(archive_path, archive_name)

        # 5. Enforce retention policy
        self._prune_old_backups(keep_count=settings.BACKUP_RETENTION_COUNT)

        backup_info = {
            "filename": archive_name,
            "filepath": archive_path,
            "size_bytes": size_bytes,
            "sha256": sha256_checksum,
            "cloud_synced": cloud_synced,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        logger.info(f"Backup completed successfully: {archive_name} ({size_bytes} bytes, sha256={sha256_checksum[:8]}...)")
        return backup_info

    def _sync_to_cloud(self, local_path: str, filename: str) -> bool:
        """
        Uploads backup archive to S3/GCS bucket if configured.
        Falls back gracefully with logging if cloud credentials are not supplied.
        """
        if not settings.BACKUP_S3_BUCKET:
            return False

        try:
            import boto3
            s3_client = boto3.client("s3", region_name=settings.BACKUP_S3_REGION)
            s3_key = f"backups/{filename}"
            s3_client.upload_file(local_path, settings.BACKUP_S3_BUCKET, s3_key)
            logger.info(f"Synced backup to s3://{settings.BACKUP_S3_BUCKET}/{s3_key}")
            return True
        except ImportError:
            logger.warning("boto3 not installed; cloud backup synchronization skipped.")
            return False
        except Exception as e:
            logger.warning(f"Cloud backup sync to S3 bucket '{settings.BACKUP_S3_BUCKET}' failed: {e}")
            return False

    def list_backups(self) -> List[Dict[str, Any]]:
        """Lists all available backup archives sorted chronologically (newest first)."""
        pattern = os.path.join(self.backup_dir, "backup_*.db.gz")
        files = glob.glob(pattern)
        files.sort(key=os.path.getmtime, reverse=True)

        results = []
        for f in files:
            fname = os.path.basename(f)
            stat = os.stat(f)
            created_at = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            results.append({
                "filename": fname,
                "size_bytes": stat.st_size,
                "created_at": created_at,
                "sha256": self._calculate_sha256(f),
                "cloud_synced": bool(settings.BACKUP_S3_BUCKET)
            })
        return results

    def restore_backup(self, filename: str) -> Dict[str, Any]:
        """
        Restores the active SQLite database from a selected backup archive.
        Creates an automatic pre-restore safety snapshot of the active database before applying.
        """
        backup_path = os.path.join(self.backup_dir, filename)
        if not os.path.exists(backup_path):
            raise FileNotFoundError(f"Backup archive '{filename}' not found.")

        db_path = self._get_sqlite_db_path()

        # 1. Take a safety snapshot of current database
        safety_label = "pre_restore_safety"
        safety_info = None
        if os.path.exists(db_path):
            safety_info = self.create_backup(label=safety_label)

        # 2. Decompress backup candidate to temp file
        temp_restore_path = os.path.join(self.backup_dir, "temp_restore_candidate.db")
        try:
            with gzip.open(backup_path, "rb") as f_in:
                with open(temp_restore_path, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)

            # 3. Verify database integrity before overwriting active database
            conn = sqlite3.connect(temp_restore_path)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check;")
            integrity_result = cursor.fetchone()
            conn.close()

            if not integrity_result or integrity_result[0] != "ok":
                raise ValueError(f"Integrity check failed on backup archive: {integrity_result}")

            # 4. Safely apply backup to target database
            dest_conn = sqlite3.connect(db_path)
            candidate_conn = sqlite3.connect(temp_restore_path)
            candidate_conn.backup(dest_conn, pages=100)
            candidate_conn.close()
            dest_conn.close()

            logger.info(f"Database successfully restored from backup '{filename}'")
            return {
                "status": "success",
                "restored_from": filename,
                "safety_backup": safety_info.get("filename") if safety_info else None,
                "restored_at": datetime.now(timezone.utc).isoformat()
            }
        finally:
            if os.path.exists(temp_restore_path):
                os.remove(temp_restore_path)

    def _prune_old_backups(self, keep_count: int = 7):
        """Removes older backups when count exceeds retention threshold."""
        pattern = os.path.join(self.backup_dir, "backup_*.db.gz")
        files = glob.glob(pattern)
        # Never prune pre_restore_safety backups automatically
        prunable_files = [f for f in files if "pre_restore_safety" not in f]
        prunable_files.sort(key=os.path.getmtime, reverse=True)

        if len(prunable_files) > keep_count:
            for old_file in prunable_files[keep_count:]:
                try:
                    os.remove(old_file)
                    logger.info(f"Pruned expired database backup: {os.path.basename(old_file)}")
                except Exception as e:
                    logger.warning(f"Failed to prune old backup {old_file}: {e}")

backup_service = BackupService()
