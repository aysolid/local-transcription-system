# core/batch_manager.py
import threading
import queue
import json
from dataclasses import dataclass, asdict
from enum import Enum
from typing import List, Dict, Optional
import os
from datetime import datetime

class BatchStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class BatchJob:
    id: str
    file_path: str
    status: BatchStatus
    progress: float
    result_path: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None
    created_at: datetime = None
    completed_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

class BatchManager:
    def __init__(self, max_workers: int = 2):
        self.jobs = {}
        self.job_queue = queue.Queue()
        self.completed_queue = queue.Queue()
        self.max_workers = max_workers
        self.workers = []
        self.is_running = False
        self.lock = threading.Lock()
        
    def add_jobs(self, file_paths: List[str], settings: Dict) -> List[str]:
        """Add multiple files to batch queue"""
        job_ids = []
        for file_path in file_paths:
            job_id = f"job_{len(self.jobs)}_{os.path.basename(file_path)}"
            job = BatchJob(
                id=job_id,
                file_path=file_path,
                status=BatchStatus.PENDING,
                progress=0.0,
                metadata={
                    'settings': settings,
                    'original_filename': os.path.basename(file_path),
                    'file_size': os.path.getsize(file_path)
                }
            )
            
            with self.lock:
                self.jobs[job_id] = job
                self.job_queue.put(job_id)
            
            job_ids.append(job_id)
        
        return job_ids
    
    def start_workers(self, trans_system):
        """Start worker threads for batch processing"""
        self.is_running = True
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                args=(trans_system,),
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
    
    def _worker_loop(self, trans_system):
        """Worker thread processing loop"""
        while self.is_running:
            try:
                job_id = self.job_queue.get(timeout=1)
                self._process_job(job_id, trans_system)
                self.job_queue.task_done()
            except queue.Empty:
                continue
    
    def _process_job(self, job_id: str, trans_system):
        """Process a single job"""
        with self.lock:
            job = self.jobs[job_id]
            job.status = BatchStatus.PROCESSING
            job.progress = 10
        
        try:
            # Update progress
            def progress_callback(pct, msg):
                with self.lock:
                    job.progress = pct
                    job.metadata['status_message'] = msg
            
            # Transcribe file
            segments = trans_system.transcribe_file(
                job.file_path,
                language=job.metadata['settings'].get('language'),
                diarize=job.metadata['settings'].get('diarize', True),
                progress_callback=progress_callback
            )
            
            # Save results
            output_dir = "./outputs/batch_results"
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"{output_dir}/{job_id}_{timestamp}.json"
            
            # Export results
            trans_system.export_transcription(
                segments,
                "json",
                output_file
            )
            
            with self.lock:
                job.status = BatchStatus.COMPLETED
                job.progress = 100.0
                job.result_path = output_file
                job.completed_at = datetime.now()
                
        except Exception as e:
            with self.lock:
                job.status = BatchStatus.FAILED
                job.error = str(e)
        
        finally:
            self.completed_queue.put(job_id)
    
    def get_job_status(self, job_id: str) -> Optional[BatchJob]:
        """Get current status of a job"""
        with self.lock:
            return self.jobs.get(job_id)
    
    def get_all_jobs(self) -> List[BatchJob]:
        """Get all jobs"""
        with self.lock:
            return list(self.jobs.values())
    
    def cancel_job(self, job_id: str):
        """Cancel a specific job"""
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].status = BatchStatus.CANCELLED
    
    def export_batch_report(self, output_path: str):
        """Export batch processing report"""
        report = {
            'total_jobs': len(self.jobs),
            'completed': sum(1 for j in self.jobs.values() 
                           if j.status == BatchStatus.COMPLETED),
            'failed': sum(1 for j in self.jobs.values() 
                         if j.status == BatchStatus.FAILED),
            'jobs': [asdict(job) for job in self.jobs.values()],
            'generated_at': datetime.now().isoformat()
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, default=str)