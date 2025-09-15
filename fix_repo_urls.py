#!/usr/bin/env python3
"""
Script to fix malformed repository URLs in the database.
This script checks for common URL errors like missing slashes in https://
and fixes them in the database.
"""

import os
import sys
import logging
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    # Load environment variables
    load_dotenv()
    
    # Get database connection string from environment or use default
    db_url = os.getenv("DB_URL", "mysql+pymysql://root:password@localhost/ai_bom")
    
    try:
        # Connect to the database
        logger.info(f"Connecting to database...")
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # First, get all projects with their URLs
            result = conn.execute(text("SELECT id, name, repo_url FROM projects"))
            projects = [{"id": row.id, "name": row.name, "repo_url": row.repo_url} for row in result]
            
            logger.info(f"Found {len(projects)} projects in database")
            
            # Check and fix URLs
            fixed_count = 0
            for project in projects:
                repo_url = project["repo_url"]
                fixed_url = repo_url
                
                # Fix common URL errors
                if repo_url.startswith("https:/github.com"):
                    fixed_url = repo_url.replace("https:/github.com", "https://github.com")
                    logger.info(f"Project {project['id']} ({project['name']}): Fixing URL from {repo_url} to {fixed_url}")
                    
                    # Update in database
                    conn.execute(
                        text("UPDATE projects SET repo_url = :url WHERE id = :id"),
                        {"url": fixed_url, "id": project["id"]}
                    )
                    fixed_count += 1
            
            if fixed_count > 0:
                conn.commit()
                logger.info(f"Fixed {fixed_count} repository URLs")
            else:
                logger.info("No URLs needed fixing")
                
    except Exception as e:
        logger.error(f"Error fixing repository URLs: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
