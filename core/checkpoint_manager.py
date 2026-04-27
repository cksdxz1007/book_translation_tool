"""
Checkpoint manager for translation job persistence and resume functionality.

This module provides the CheckpointManager class for managing translation job
checkpoints with SQLite database persistence.
"""

import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime


class CheckpointManager:
    """
    Manages translation job checkpoints with database persistence.

    Provides functionality for:
    - Starting new translation jobs and tracking their progress
    - Saving checkpoints after translating each chunk
    - Loading checkpoints to resume interrupted jobs
    - Querying resumable jobs for recovery

    Database Schema:
        translation_jobs: Stores job metadata and status
        translation_chunks: Stores individual chunk translations

    Example:
        >>> manager = CheckpointManager()
        >>> manager.start_job("job123", "pdf", {"source": "en", "target": "zh"})
        >>> manager.save_checkpoint("job123", 0, "Hello", "你好")
        >>> checkpoint = manager.load_checkpoint("job123")
    """

    def __init__(self, db_path: str = "data/checkpoints.db"):
        """
        Initialize the CheckpointManager.

        Args:
            db_path: Path to SQLite database file. Default is "data/checkpoints.db".
        """
        self.db_path = db_path
        self.uploads_dir = Path("data/uploads")
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self._init_database()

    def _init_database(self):
        """
        Initialize SQLite database with translation_jobs and translation_chunks tables.

        Creates the database and tables if they don't exist.
        Sets up foreign key relationship between chunks and jobs.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Enable foreign keys
        cursor.execute("PRAGMA foreign_keys = ON")

        # Create translation_jobs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS translation_jobs (
                translation_id TEXT PRIMARY KEY,
                file_type TEXT,
                config TEXT,
                status TEXT DEFAULT 'running',
                created_at TEXT,
                updated_at TEXT,
                progress TEXT
            )
        ''')

        # Create translation_chunks table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS translation_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                translation_id TEXT,
                chunk_index INTEGER,
                original_text TEXT,
                translated_text TEXT,
                chunk_data TEXT,
                status TEXT,
                created_at TEXT,
                FOREIGN KEY (translation_id) REFERENCES translation_jobs(translation_id)
            )
        ''')

        # Create index on translation_id for faster lookups
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_chunks_translation_id
            ON translation_chunks(translation_id)
        ''')

        conn.commit()
        conn.close()

    def start_job(self, translation_id: str, file_type: str,
                  config: Dict[str, Any], input_file_path: Optional[str] = None) -> bool:
        """
        Start tracking a new translation job.

        Args:
            translation_id: Unique identifier for the job.
            file_type: Type of file being translated (e.g., "pdf", "epub", "markdown").
            config: Translation configuration dictionary.
            input_file_path: Optional path to input file for preservation.

        Returns:
            True if job started successfully, False otherwise.
        """
        # Preserve input file if provided
        if input_file_path:
            self._preserve_input_file(translation_id, input_file_path, config)

        now = datetime.now().isoformat()
        progress = {
            'total_chunks': 0,
            'completed_chunks': 0,
            'failed_chunks': 0,
            'current_chunk_index': -1
        }

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO translation_jobs (translation_id, file_type, config, status, created_at, updated_at, progress)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (translation_id, file_type, json.dumps(config), 'running', now, now, json.dumps(progress)))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # Job already exists
            return False
        finally:
            conn.close()

    def _preserve_input_file(self, translation_id: str, input_file_path: str, config: Dict[str, Any]):
        """
        Preserve the input file for resume capability.

        Args:
            translation_id: Job identifier.
            input_file_path: Original input file path.
            config: Translation configuration (will be updated with preserved path).
        """
        input_path = Path(input_file_path)

        if not input_path.exists():
            return

        # Preserve in uploads directory with job ID subdirectory
        job_upload_dir = self.uploads_dir / translation_id
        job_upload_dir.mkdir(parents=True, exist_ok=True)

        # Keep the original filename
        preserved_path = job_upload_dir / input_path.name

        try:
            import shutil
            shutil.copy2(input_file_path, preserved_path)
            config['preserved_input_path'] = str(preserved_path)
        except Exception as e:
            print(f"Warning: Could not preserve input file: {e}")

    def save_checkpoint(self, translation_id: str, chunk_index: int,
                       original_text: str, translated_text: Optional[str],
                       chunk_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Save a checkpoint after translating a chunk.

        Args:
            translation_id: Job identifier.
            chunk_index: Index of the chunk being saved.
            original_text: Original text content of the chunk.
            translated_text: Translated text (None if translation failed).
            chunk_data: Optional additional metadata for the chunk.

        Returns:
            True if saved successfully, False otherwise.
        """
        status = 'completed' if translated_text else 'failed'
        now = datetime.now().isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO translation_chunks (translation_id, chunk_index, original_text, translated_text, chunk_data, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (translation_id, chunk_index, original_text, translated_text,
                  json.dumps(chunk_data) if chunk_data else None, status, now))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving checkpoint: {e}")
            return False
        finally:
            conn.close()

    def load_checkpoint(self, translation_id: str) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint data for a job.

        Args:
            translation_id: Job identifier.

        Returns:
            Dictionary containing job data, chunks, and resume information:
                - job: Job metadata and config
                - chunks: List of completed/failed chunks
                - resume_from_index: Index to resume translation from
            Returns None if job not found.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            # Get job data
            cursor.execute('SELECT * FROM translation_jobs WHERE translation_id = ?', (translation_id,))
            job_row = cursor.fetchone()

            if not job_row:
                return None

            # Get all chunks for this job
            cursor.execute('''
                SELECT * FROM translation_chunks
                WHERE translation_id = ?
                ORDER BY chunk_index
            ''', (translation_id,))
            chunk_rows = cursor.fetchall()

            conn.close()

            # Build job dictionary with parsed JSON fields
            job = dict(job_row)
            job['config'] = json.loads(job['config'])
            job['progress'] = json.loads(job['progress'])

            # Build chunks list
            chunks = []
            for row in chunk_rows:
                chunk = dict(row)
                if chunk['chunk_data']:
                    chunk['chunk_data'] = json.loads(chunk['chunk_data'])
                chunks.append(chunk)

            # Determine resume point based on last completed chunk
            resume_from_index = job['progress'].get('current_chunk_index', -1) + 1

            return {
                'job': job,
                'chunks': chunks,
                'resume_from_index': resume_from_index
            }

        except Exception as e:
            print(f"Error loading checkpoint: {e}")
            if conn:
                conn.close()
            return None

    def update_job_progress(self, translation_id: str, **kwargs) -> bool:
        """
        Update job progress fields.

        Args:
            translation_id: Job identifier.
            **kwargs: Progress fields to update (e.g., current_chunk_index, total_chunks, completed_chunks).

        Returns:
            True if updated successfully, False otherwise.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get current progress
            cursor.execute('SELECT progress FROM translation_jobs WHERE translation_id = ?', (translation_id,))
            row = cursor.fetchone()

            if not row:
                return False

            progress = json.loads(row[0])

            # Update progress with new values
            progress.update(kwargs)

            # Update database
            cursor.execute('''
                UPDATE translation_jobs
                SET progress = ?, updated_at = ?
                WHERE translation_id = ?
            ''', (json.dumps(progress), datetime.now().isoformat(), translation_id))

            conn.commit()
            return True

        except Exception as e:
            print(f"Error updating job progress: {e}")
            return False
        finally:
            conn.close()

    def mark_completed(self, translation_id: str) -> bool:
        """
        Mark a job as completed.

        Args:
            translation_id: Job identifier.

        Returns:
            True if marked successfully, False otherwise.
        """
        return self.update_job_progress(translation_id, status='completed')

    def mark_interrupted(self, translation_id: str) -> bool:
        """
        Mark a job as interrupted.

        Args:
            translation_id: Job identifier.

        Returns:
            True if marked successfully, False otherwise.
        """
        return self.update_job_progress(translation_id, status='interrupted')

    def get_resumable_jobs(self) -> List[Dict[str, Any]]:
        """
        Get all jobs that can be resumed.

        Returns:
            List of job dictionaries with resumable status (running or interrupted).
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM translation_jobs
                WHERE status IN ('running', 'interrupted')
                ORDER BY created_at DESC
            """)
            rows = cursor.fetchall()
            conn.close()

            jobs = []
            for row in rows:
                job = dict(row)
                job['config'] = json.loads(job['config'])
                job['progress'] = json.loads(job['progress'])

                # Calculate progress percentage
                total = job['progress'].get('total_chunks', 0)
                completed = job['progress'].get('completed_chunks', 0)
                if total > 0:
                    job['progress_percentage'] = int((completed / total) * 100)
                else:
                    job['progress_percentage'] = 0

                jobs.append(job)

            return jobs

        except Exception as e:
            print(f"Error getting resumable jobs: {e}")
            if conn:
                conn.close()
            return []

    def get_job(self, translation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job information by translation ID.

        Args:
            translation_id: Job identifier.

        Returns:
            Job dictionary or None if not found.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute('SELECT * FROM translation_jobs WHERE translation_id = ?', (translation_id,))
            row = cursor.fetchone()
            conn.close()

            if not row:
                return None

            job = dict(row)
            job['config'] = json.loads(job['config'])
            job['progress'] = json.loads(job['progress'])

            return job

        except Exception as e:
            print(f"Error getting job: {e}")
            if conn:
                conn.close()
            return None

    def mark_running(self, translation_id: str) -> bool:
        """
        Mark a job as running (resumed from interrupted).

        Args:
            translation_id: Job identifier.

        Returns:
            True if marked successfully, False otherwise.
        """
        return self.update_job_progress(translation_id, status='running')

    def delete_job(self, translation_id: str) -> bool:
        """
        Delete a job and all its associated chunks.

        Args:
            translation_id: Job identifier.

        Returns:
            True if deleted successfully, False otherwise.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Delete chunks first (foreign key constraint)
            cursor.execute('DELETE FROM translation_chunks WHERE translation_id = ?', (translation_id,))
            # Delete job
            cursor.execute('DELETE FROM translation_jobs WHERE translation_id = ?', (translation_id,))
            conn.commit()
            return True

        except Exception as e:
            print(f"Error deleting job: {e}")
            return False
        finally:
            conn.close()

    def get_chunks(self, translation_id: str) -> List[Dict[str, Any]]:
        """
        Get all chunks for a translation job.

        Args:
            translation_id: Job identifier.

        Returns:
            List of chunk dictionaries ordered by chunk_index.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT * FROM translation_chunks
                WHERE translation_id = ?
                ORDER BY chunk_index
            ''', (translation_id,))
            rows = cursor.fetchall()
            conn.close()

            chunks = []
            for row in rows:
                chunk = dict(row)
                if chunk['chunk_data']:
                    chunk['chunk_data'] = json.loads(chunk['chunk_data'])
                chunks.append(chunk)

            return chunks

        except Exception as e:
            print(f"Error getting chunks: {e}")
            if conn:
                conn.close()
            return []

    def cleanup_old_jobs(self, max_age_days: int = 30) -> int:
        """
        Clean up jobs older than max_age_days.

        Args:
            max_age_days: Maximum age in days for jobs to keep.

        Returns:
            Number of jobs deleted.
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=max_age_days)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Get old job IDs for file cleanup
            cursor.execute("""
                SELECT translation_id FROM translation_jobs
                WHERE created_at < ?
            """, (cutoff.isoformat(),))
            old_job_ids = [row[0] for row in cursor.fetchall()]

            # Delete old jobs (chunks deleted via CASCADE)
            cursor.execute("""
                DELETE FROM translation_jobs
                WHERE created_at < ?
            """, (cutoff.isoformat(),))

            conn.commit()
            conn.close()

            # Clean up upload directories for deleted jobs
            for job_id in old_job_ids:
                job_upload_dir = self.uploads_dir / job_id
                if job_upload_dir.exists():
                    import shutil
                    try:
                        shutil.rmtree(job_upload_dir)
                    except Exception as e:
                        print(f"Warning: Could not delete upload directory for {job_id}: {e}")

            return len(old_job_ids)

        except Exception as e:
            print(f"Error cleaning up old jobs: {e}")
            if conn:
                conn.close()
            return 0

    def close(self):
        """
        Close database connection.

        Note: This implementation uses connection-per-operation pattern,
        so there's no persistent connection to close. This method is
        provided for API compatibility.
        """
        pass