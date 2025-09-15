"""
Runtime collector for integrating runtime tracing with the ML-BOM workflow.

This module provides the interface between the runtime tracer and the
existing ML-BOM generation pipeline.
"""

import time
import logging
from typing import List, Dict, Optional
from dataclasses import asdict

from .tracer import RuntimeTracer, RuntimeEvent
from .normalizer import RuntimeNormalizer
from ..schemas.models import NormalizedArtifact
from ..db.connection import db_manager

logger = logging.getLogger(__name__)

class RuntimeCollector:
    """
    Collects and processes runtime AI/ML artifact usage.
    
    This class manages the runtime tracing lifecycle and integrates
    captured events with the existing ML-BOM workflow.
    """
    
    def __init__(self, project_id: int):
        self.project_id = project_id
        self.tracer = RuntimeTracer(project_id)
        self.normalizer = RuntimeNormalizer()
        self._db = None
    
    @property
    def db(self):
        """Lazy database connection."""
        # We need to use the raw connection, not the SQLAlchemy session
        if self._db is None:
            # Get the underlying MySQL connection from the session
            session = db_manager.get_session()
            self._db = session.connection().connection
        return self._db
    
    def start_collection(self) -> bool:
        """
        Start runtime collection for the project.
        
        Returns:
            True if collection started successfully, False otherwise
        """
        logger.info(f"Starting runtime collection for project {self.project_id}")
        
        success = self.tracer.start()
        if success:
            logger.info("Runtime collection started successfully")
        else:
            logger.error("Failed to start runtime collection")
        
        return success
    
    def stop_collection(self) -> List[NormalizedArtifact]:
        """
        Stop runtime collection and return normalized artifacts.
        
        Returns:
            List of normalized AI artifacts discovered during runtime
        """
        logger.info("Stopping runtime collection")
        
        self.tracer.stop()
        events = self.tracer.get_events()
        
        if not events:
            logger.info("No runtime events captured")
            return []
        
        logger.info(f"Captured {len(events)} runtime events")
        
        # Normalize events to artifacts
        artifacts = self.normalizer.normalize_events(events)
        
        # Store runtime events in database
        self._store_runtime_events(events)
        
        logger.info(f"Normalized to {len(artifacts)} unique artifacts")
        return artifacts
    
    def collect_for_duration(self, duration_seconds: int) -> List[NormalizedArtifact]:
        """
        Collect runtime events for a specified duration.
        
        Args:
            duration_seconds: How long to collect events
            
        Returns:
            List of normalized AI artifacts
        """
        logger.info(f"Collecting runtime events for {duration_seconds} seconds")
        
        if not self.start_collection():
            return []
        
        try:
            time.sleep(duration_seconds)
        except KeyboardInterrupt:
            logger.info("Collection interrupted by user")
        
        return self.stop_collection()
    
    def get_collection_summary(self) -> Dict:
        """Get a summary of the current collection session."""
        return self.tracer.get_summary()
    
    def _store_runtime_events(self, events: List[RuntimeEvent]):
        """Store runtime events in the database."""
        if not events:
            return
        
        try:
            # Create runtime_events table if it doesn't exist
            self._ensure_runtime_events_table()
            
            # Insert events
            insert_query = """
            INSERT INTO runtime_events 
            (project_id, ts, pid, process_name, syscall, path, source_url, type, hash, meta)
            VALUES (%s, FROM_UNIXTIME(%s), %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            cursor = self.db.cursor()
            
            for event in events:
                cursor.execute(insert_query, (
                    self.project_id,
                    event.timestamp,
                    event.pid,
                    event.process_name,
                    event.syscall,
                    event.path,
                    event.source_url,
                    event.artifact_type,
                    event.hash,
                    str(event.metadata) if event.metadata else None
                ))
            
            self.db.commit()
            logger.info(f"Stored {len(events)} runtime events in database")
            
        except Exception as e:
            logger.error(f"Failed to store runtime events: {e}")
            self.db.rollback()
    
    def _ensure_runtime_events_table(self):
        """Ensure the runtime_events table exists."""
        create_table_query = """
        CREATE TABLE IF NOT EXISTS runtime_events (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            project_id BIGINT NOT NULL,
            ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            pid INT,
            process_name VARCHAR(255),
            syscall VARCHAR(64),
            path TEXT,
            source_url TEXT,
            type ENUM('model','dataset','prompt','tool') NULL,
            hash CHAR(64),
            meta JSON,
            KEY idx_proj_ts (project_id, ts),
            KEY idx_type (type),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
        """
        
        try:
            cursor = self.db.cursor()
            cursor.execute(create_table_query)
            self.db.commit()
            
            # Try to add FULLTEXT index if supported
            try:
                cursor.execute("ALTER TABLE runtime_events ADD FULLTEXT KEY ft_path (path)")
                self.db.commit()
                logger.debug("Added FULLTEXT index to runtime_events.path")
            except Exception:
                # FULLTEXT not supported, that's okay
                pass
                
        except Exception as e:
            logger.error(f"Failed to create runtime_events table: {e}")
            raise
    
    def get_runtime_events(self, limit: int = 100) -> List[Dict]:
        """
        Get recent runtime events for the project.
        
        Args:
            limit: Maximum number of events to return
            
        Returns:
            List of runtime event dictionaries
        """
        try:
            query = """
            SELECT id, ts, pid, process_name, syscall, path, source_url, type, hash, meta
            FROM runtime_events 
            WHERE project_id = %s 
            ORDER BY ts DESC 
            LIMIT %s
            """
            
            cursor = self.db.cursor(dictionary=True)
            cursor.execute(query, (self.project_id, limit))
            
            events = cursor.fetchall()
            
            # Convert timestamps to Unix timestamps
            for event in events:
                if event['ts']:
                    event['ts'] = event['ts'].timestamp()
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to get runtime events: {e}")
            return []
    
    def clear_runtime_events(self):
        """Clear all runtime events for the project."""
        try:
            cursor = self.db.cursor()
            cursor.execute("DELETE FROM runtime_events WHERE project_id = %s", (self.project_id,))
            self.db.commit()
            
            # Also clear tracer events
            self.tracer.clear_events()
            
            logger.info(f"Cleared runtime events for project {self.project_id}")
            
        except Exception as e:
            logger.error(f"Failed to clear runtime events: {e}")
            self.db.rollback()

class RuntimeIntegration:
    """
    Integration layer for adding runtime collection to existing workflows.
    
    This class provides methods to seamlessly integrate runtime tracing
    with the existing static analysis workflow.
    """
    
    @staticmethod
    def enhance_scan_with_runtime(project_id: int, static_artifacts: List[NormalizedArtifact], 
                                 collection_duration: int = 30) -> List[NormalizedArtifact]:
        """
        Enhance static scan results with runtime collection.
        
        Args:
            project_id: Project ID
            static_artifacts: Artifacts from static analysis
            collection_duration: How long to collect runtime events (seconds)
            
        Returns:
            Combined list of static and runtime artifacts
        """
        logger.info(f"Enhancing scan with runtime collection for {collection_duration}s")
        
        collector = RuntimeCollector(project_id)
        
        # Collect runtime artifacts
        runtime_artifacts = collector.collect_for_duration(collection_duration)
        
        # Combine and deduplicate
        all_artifacts = static_artifacts + runtime_artifacts
        
        # Deduplicate by canonical ID
        seen_ids = set()
        unique_artifacts = []
        
        for artifact in all_artifacts:
            if artifact.id not in seen_ids:
                unique_artifacts.append(artifact)
                seen_ids.add(artifact.id)
            else:
                # If we have both static and runtime versions, prefer runtime
                if artifact.metadata and artifact.metadata.get('runtime_detected'):
                    # Replace static version with runtime version
                    for i, existing in enumerate(unique_artifacts):
                        if existing.id == artifact.id:
                            unique_artifacts[i] = artifact
                            break
        
        logger.info(f"Combined {len(static_artifacts)} static + {len(runtime_artifacts)} runtime = {len(unique_artifacts)} unique artifacts")
        
        return unique_artifacts
    
    @staticmethod
    def get_runtime_summary(project_id: int) -> Dict:
        """Get runtime collection summary for a project."""
        collector = RuntimeCollector(project_id)
        
        # Get recent events
        events = collector.get_runtime_events(limit=1000)
        
        if not events:
            return {"total_events": 0, "runtime_enabled": False}
        
        # Calculate summary
        summary = {
            "total_events": len(events),
            "runtime_enabled": True,
            "by_type": {},
            "by_process": {},
            "recent_activity": []
        }
        
        for event in events:
            # Count by type
            event_type = event.get('type') or 'unknown'
            summary["by_type"][event_type] = summary["by_type"].get(event_type, 0) + 1
            
            # Count by process
            process = event.get('process_name') or 'unknown'
            summary["by_process"][process] = summary["by_process"].get(process, 0) + 1
        
        # Get recent activity (last 10 events)
        summary["recent_activity"] = events[:10]
        
        return summary