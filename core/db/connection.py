import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from decouple import config
import logging

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self):
        # Build from components for TiDB Cloud
        db_host = config('TIDB_URL')
        db_user = config('DB_USER')
        db_pass = config('DB_PASS') 
        db_name = config('DB_NAME')
        
        # TiDB Cloud connection format - secure connection required
        self.tidb_url = f"mysql+pymysql://{db_user}:{db_pass}@{db_host}:4000/{db_name}"
        
        self.engine = create_engine(
            self.tidb_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False,
            connect_args={"ssl": {"ssl_disabled": False}}
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.capabilities = self._detect_capabilities()
    
    def _detect_capabilities(self):
        """Detect TiDB capabilities at startup"""
        capabilities = {
            'vector': False,
            'fulltext': False,
            'version': None
        }
        
        try:
            with self.engine.connect() as conn:
                # Check TiDB version
                result = conn.execute(text("SELECT VERSION()"))
                version = result.scalar()
                capabilities['version'] = version
                logger.info(f"TiDB Version: {version}")
                
                # Test vector support
                try:
                    conn.execute(text("SELECT 1 WHERE VEC_COSINE_DISTANCE('[1,2,3]', '[1,2,3]') IS NOT NULL"))
                    capabilities['vector'] = True
                    logger.info("Vector functions available")
                except Exception as e:
                    logger.warning(f"Vector functions not available: {e}")
                
                # Test fulltext support - this will be done in migrations.py
                # to set the global FTS_ENABLED flag
                capabilities['fulltext'] = False  # Will be updated by migrations
                    
        except Exception as e:
            logger.error(f"Failed to detect capabilities: {e}")
            
        return capabilities
    
    def get_session(self):
        return self.SessionLocal()
    
    def health_check(self):
        """Health check for the database connection"""
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"status": "healthy", "capabilities": self.capabilities}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

# Global database manager instance
db_manager = DatabaseManager()