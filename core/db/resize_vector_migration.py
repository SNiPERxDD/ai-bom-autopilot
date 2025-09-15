"""
Vector Column Resize Migration

This migration script handles resizing the emb VECTOR column in evidence_chunks table
to support different embedding providers with different dimensions:
- OpenAI: 1536 dimensions
- Gemini: 768 dimensions

The script provides safe migration with data preservation and rollback capabilities.
"""

from sqlalchemy import text
from core.db.connection import db_manager
from decouple import config
import logging
import argparse
import sys

logger = logging.getLogger(__name__)

def get_current_vector_dimension():
    """Get the current vector dimension of the emb column"""
    try:
        with db_manager.engine.connect() as conn:
            # Query information_schema to get column definition
            result = conn.execute(text("""
                SELECT COLUMN_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'evidence_chunks' 
                AND COLUMN_NAME = 'emb'
            """))
            
            column_type = result.scalar()
            if column_type:
                # Extract dimension from VECTOR(n) format
                if 'VECTOR(' in column_type:
                    start = column_type.find('VECTOR(') + 7
                    end = column_type.find(')', start)
                    return int(column_type[start:end])
            
            return None
    except Exception as e:
        logger.error(f"Failed to get current vector dimension: {e}")
        return None

def check_table_exists():
    """Check if evidence_chunks table exists"""
    try:
        with db_manager.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = DATABASE() 
                AND TABLE_NAME = 'evidence_chunks'
            """))
            return result.scalar() > 0
    except Exception as e:
        logger.error(f"Failed to check table existence: {e}")
        return False

def check_vector_support():
    """Check if TiDB supports vector functions"""
    try:
        with db_manager.engine.connect() as conn:
            conn.execute(text("SELECT VEC_COSINE_DISTANCE('[1,2,3]', '[1,2,3]')"))
            return True
    except Exception as e:
        logger.warning(f"Vector functions not available: {e}")
        return False

def get_row_count():
    """Get the number of rows in evidence_chunks table"""
    try:
        with db_manager.engine.connect() as conn:
            result = conn.execute(text("SELECT COUNT(*) FROM evidence_chunks"))
            return result.scalar()
    except Exception as e:
        logger.error(f"Failed to get row count: {e}")
        return 0

def backup_vector_data():
    """Create a backup of vector data before migration"""
    try:
        with db_manager.engine.connect() as conn:
            # Create backup table with current timestamp
            backup_table = f"evidence_chunks_backup_{int(__import__('time').time())}"
            
            conn.execute(text(f"""
                CREATE TABLE {backup_table} AS 
                SELECT id, emb FROM evidence_chunks WHERE emb IS NOT NULL
            """))
            
            logger.info(f"Created backup table: {backup_table}")
            return backup_table
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return None

def resize_vector_column(new_dimension: int, preserve_data: bool = True):
    """
    Resize the vector column to new dimension
    
    Args:
        new_dimension: Target dimension (768 or 1536)
        preserve_data: Whether to preserve existing data (default: True)
    """
    if not check_table_exists():
        logger.error("evidence_chunks table does not exist. Run migrations first.")
        return False
    
    if not check_vector_support():
        logger.error("Vector functions not supported in this TiDB instance")
        return False
    
    current_dim = get_current_vector_dimension()
    if current_dim is None:
        logger.error("Could not determine current vector dimension")
        return False
    
    if current_dim == new_dimension:
        logger.info(f"Vector column already has dimension {new_dimension}, no migration needed")
        return True
    
    row_count = get_row_count()
    logger.info(f"Current vector dimension: {current_dim}")
    logger.info(f"Target vector dimension: {new_dimension}")
    logger.info(f"Rows in evidence_chunks: {row_count}")
    
    # Create backup if preserving data and there are rows
    backup_table = None
    if preserve_data and row_count > 0:
        backup_table = backup_vector_data()
        if not backup_table:
            logger.error("Failed to create backup, aborting migration")
            return False
    
    try:
        with db_manager.engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                if preserve_data and row_count > 0:
                    # Clear vector data before resize (TiDB requirement)
                    logger.info("Clearing vector data before column resize...")
                    conn.execute(text("UPDATE evidence_chunks SET emb = NULL"))
                
                # Resize the vector column
                logger.info(f"Resizing vector column to VECTOR({new_dimension})...")
                conn.execute(text(f"""
                    ALTER TABLE evidence_chunks 
                    MODIFY COLUMN emb VECTOR({new_dimension})
                """))
                
                # Recreate vector index if it exists
                try:
                    logger.info("Recreating vector index...")
                    conn.execute(text("ALTER TABLE evidence_chunks DROP INDEX vec_idx"))
                except:
                    pass  # Index might not exist
                
                conn.execute(text("ALTER TABLE evidence_chunks ADD VECTOR INDEX vec_idx (emb)"))
                
                # Commit the transaction
                trans.commit()
                
                logger.info(f"✅ Successfully resized vector column to {new_dimension} dimensions")
                
                if preserve_data and row_count > 0:
                    logger.warning("⚠️  Vector data was cleared during resize")
                    logger.warning("   You need to re-embed existing chunks with the new provider")
                    logger.warning(f"   Backup available in table: {backup_table}")
                
                return True
                
            except Exception as e:
                trans.rollback()
                logger.error(f"Migration failed, rolled back: {e}")
                return False
                
    except Exception as e:
        logger.error(f"Failed to start migration transaction: {e}")
        return False

def validate_migration(expected_dimension: int):
    """Validate that the migration completed successfully"""
    current_dim = get_current_vector_dimension()
    
    if current_dim == expected_dimension:
        logger.info(f"✅ Migration validation passed: dimension is {expected_dimension}")
        return True
    else:
        logger.error(f"❌ Migration validation failed: expected {expected_dimension}, got {current_dim}")
        return False

def auto_resize_for_provider():
    """Automatically resize based on current EMBED_PROVIDER configuration"""
    provider = config('EMBED_PROVIDER', default='openai').lower()
    embedding_dim = config('EMBEDDING_DIM', cast=int, default=None)
    
    if not embedding_dim:
        logger.error("EMBEDDING_DIM environment variable not set")
        return False
    
    # Validate provider-dimension combination
    if provider == 'openai' and embedding_dim not in [1536, 3072]:
        logger.warning(f"Unusual dimension {embedding_dim} for OpenAI provider")
    elif provider == 'gemini' and embedding_dim != 768:
        logger.warning(f"Unusual dimension {embedding_dim} for Gemini provider")
    
    logger.info(f"Auto-resizing for provider: {provider}, dimension: {embedding_dim}")
    
    success = resize_vector_column(embedding_dim)
    if success:
        return validate_migration(embedding_dim)
    return False

def migration_cli():
    """CLI interface for vector column migration"""
    parser = argparse.ArgumentParser(description='ML-BOM Autopilot Vector Column Migration')
    parser.add_argument('command', choices=['auto', 'resize', 'status'], 
                       help='Migration command')
    parser.add_argument('--dimension', type=int, choices=[768, 1536, 3072],
                       help='Target vector dimension (required for resize command)')
    parser.add_argument('--no-preserve', action='store_true',
                       help='Do not preserve existing data (faster migration)')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = config('LOG_LEVEL', default='INFO')
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.command == 'status':
        print("🔍 Vector Column Status")
        print("=" * 40)
        
        if not check_table_exists():
            print("❌ evidence_chunks table does not exist")
            sys.exit(1)
        
        if not check_vector_support():
            print("❌ Vector functions not supported")
            sys.exit(1)
        
        current_dim = get_current_vector_dimension()
        if current_dim:
            print(f"✅ Current vector dimension: {current_dim}")
        else:
            print("❌ Could not determine vector dimension")
            sys.exit(1)
        
        row_count = get_row_count()
        print(f"📊 Rows in evidence_chunks: {row_count}")
        
        # Show current configuration
        provider = config('EMBED_PROVIDER', default='openai')
        embedding_dim = config('EMBEDDING_DIM', cast=int, default=None)
        print(f"🔧 Current provider: {provider}")
        print(f"🔧 Configured dimension: {embedding_dim}")
        
        if embedding_dim and current_dim != embedding_dim:
            print(f"⚠️  Dimension mismatch! Run migration to resize to {embedding_dim}")
    
    elif args.command == 'auto':
        print("🚀 Auto-resizing vector column based on EMBED_PROVIDER...")
        success = auto_resize_for_provider()
        if not success:
            sys.exit(1)
    
    elif args.command == 'resize':
        if not args.dimension:
            print("❌ --dimension required for resize command")
            sys.exit(1)
        
        print(f"🚀 Resizing vector column to {args.dimension} dimensions...")
        preserve_data = not args.no_preserve
        success = resize_vector_column(args.dimension, preserve_data)
        if success:
            success = validate_migration(args.dimension)
        
        if not success:
            sys.exit(1)
    
    print("✅ Migration completed successfully!")

if __name__ == "__main__":
    migration_cli()