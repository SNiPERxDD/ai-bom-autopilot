from sqlalchemy import text
from core.db.connection import db_manager
import logging
import sys
import argparse
from decouple import config

logger = logging.getLogger(__name__)

# Global flag for FTS availability
FTS_ENABLED = False

def test_fulltext_support():
    """Test if FULLTEXT indexes are supported and set global flag"""
    global FTS_ENABLED
    
    try:
        with db_manager.engine.connect() as conn:
            # Try to create a temporary table with FULLTEXT index
            conn.execute(text("""
                CREATE TEMPORARY TABLE test_fulltext_support (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    content TEXT,
                    FULLTEXT KEY ft_content (content)
                )
            """))
            FTS_ENABLED = True
            logger.info("✅ FULLTEXT indexes supported - using TiDB FTS")
            return True
    except Exception as e:
        FTS_ENABLED = False
        logger.warning(f"❌ FULLTEXT indexes not supported - falling back to BM25: {e}")
        return False

def run_migrations():
    """Run database migrations"""
    engine = db_manager.engine
    capabilities = db_manager.capabilities
    
    # Test FULLTEXT support and set global flag
    test_fulltext_support()
    
    migrations = [
        """
        CREATE TABLE IF NOT EXISTS projects(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          name VARCHAR(255) UNIQUE,
          repo_url TEXT,
          default_branch VARCHAR(64)
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS models(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          project_id BIGINT, 
          name VARCHAR(255), 
          provider VARCHAR(128),
          version VARCHAR(128), 
          license VARCHAR(128),
          source_url TEXT, 
          repo_path TEXT, 
          commit_sha CHAR(40), 
          meta JSON,
          CONSTRAINT fk_models_project FOREIGN KEY (project_id) REFERENCES projects(id),
          UNIQUE KEY uk_model (project_id, name, provider, version)
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS datasets(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          project_id BIGINT, 
          name VARCHAR(255), 
          version VARCHAR(128),
          license VARCHAR(128), 
          source_url TEXT, 
          commit_sha CHAR(40), 
          meta JSON,
          CONSTRAINT fk_datasets_project FOREIGN KEY (project_id) REFERENCES projects(id),
          UNIQUE KEY uk_dataset (project_id, name, version)
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS prompt_blobs(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          sha CHAR(64) UNIQUE,
          content LONGTEXT
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS prompts(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          project_id BIGINT, 
          name VARCHAR(255), 
          version VARCHAR(64),
          path TEXT, 
          commit_sha CHAR(40), 
          blob_sha CHAR(64), 
          meta JSON,
          CONSTRAINT fk_prompts_project FOREIGN KEY (project_id) REFERENCES projects(id),
          KEY idx_prompts_blob (blob_sha)
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS tools(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          project_id BIGINT, 
          name VARCHAR(255), 
          version VARCHAR(128),
          type ENUM('api','lib','mcp'), 
          spec JSON, 
          meta JSON,
          CONSTRAINT fk_tools_project FOREIGN KEY (project_id) REFERENCES projects(id)
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS boms(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          project_id BIGINT, 
          bom_json JSON,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          CONSTRAINT fk_boms_project FOREIGN KEY (project_id) REFERENCES projects(id)
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS bom_diffs(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          project_id BIGINT, 
          from_bom BIGINT, 
          to_bom BIGINT,
          summary JSON, 
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          CONSTRAINT fk_diffs_from FOREIGN KEY (from_bom) REFERENCES boms(id),
          CONSTRAINT fk_diffs_to   FOREIGN KEY (to_bom)   REFERENCES boms(id)
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS policies(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          rule VARCHAR(255), 
          severity ENUM('low','medium','high'),
          spec JSON
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS policy_overrides(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          project_id BIGINT, 
          rule VARCHAR(255),
          expiration_date DATETIME, 
          reason TEXT
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS policy_events(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          project_id BIGINT, 
          severity ENUM('low','medium','high'),
          rule VARCHAR(255), 
          artifact JSON, 
          details JSON,
          dedupe_key VARCHAR(255),
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS suppressions(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          event_id BIGINT, 
          reason TEXT
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS actions(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          project_id BIGINT, 
          kind ENUM('slack','jira','email'),
          payload JSON, 
          response JSON, 
          status ENUM('ok','fail') DEFAULT 'ok',
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]
    
    # Evidence chunks table - conditional on vector support
    if capabilities['vector']:
        evidence_sql = """
        CREATE TABLE IF NOT EXISTS evidence_chunks(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          project_id BIGINT,
          ref_type ENUM('file','card','config','readme'),
          ref_path TEXT, 
          commit_sha CHAR(40), 
          chunk_ix INT,
          text LONGTEXT, 
          token_count INT,
          emb VECTOR(1536),
          meta JSON,
          KEY idx_evidence_proj_type (project_id, ref_type),
          CONSTRAINT fk_evidence_project FOREIGN KEY (project_id) REFERENCES projects(id)
        )
        """
    else:
        # Fallback without vector column
        evidence_sql = """
        CREATE TABLE IF NOT EXISTS evidence_chunks(
          id BIGINT PRIMARY KEY AUTO_INCREMENT,
          project_id BIGINT,
          ref_type ENUM('file','card','config','readme'),
          ref_path TEXT, 
          commit_sha CHAR(40), 
          chunk_ix INT,
          text LONGTEXT, 
          token_count INT,
          meta JSON,
          KEY idx_evidence_proj_type (project_id, ref_type),
          CONSTRAINT fk_evidence_project FOREIGN KEY (project_id) REFERENCES projects(id)
        )
        """
    
    migrations.append(evidence_sql)
    
    with engine.connect() as conn:
        for i, migration in enumerate(migrations):
            try:
                conn.execute(text(migration))
                logger.info(f"Migration {i+1} completed successfully")
            except Exception as e:
                logger.error(f"Migration {i+1} failed: {e}")
                raise
        
        # Add fulltext index if supported
        if FTS_ENABLED:
            try:
                conn.execute(text("ALTER TABLE evidence_chunks ADD FULLTEXT KEY ft_text (text)"))
                logger.info("✅ FULLTEXT index added to evidence_chunks")
            except Exception as e:
                logger.warning(f"❌ Failed to add FULLTEXT index: {e}")
        
        # Add vector index if supported
        if capabilities['vector']:
            try:
                conn.execute(text("ALTER TABLE evidence_chunks ADD VECTOR INDEX vec_idx (emb)"))
                logger.info("Vector index added to evidence_chunks")
            except Exception as e:
                logger.warning(f"Failed to add vector index: {e}")
        
        conn.commit()
    
    logger.info("All migrations completed successfully")

def seed_policies():
    """Seed default policies"""
    default_policies = [
        {
            'rule': 'missing_license',
            'severity': 'high',
            'spec': {'description': 'Artifact lacks SPDX-mapped license'}
        },
        {
            'rule': 'unapproved_license',
            'severity': 'high',
            'spec': {
                'description': 'License not in allowlist',
                'allowed_licenses': ['MIT', 'Apache-2.0', 'BSD-3-Clause', 'GPL-3.0']
            }
        },
        {
            'rule': 'unknown_provider',
            'severity': 'medium',
            'spec': {'description': 'Model/dataset source URL unknown'}
        },
        {
            'rule': 'model_bump_major',
            'severity': 'medium',
            'spec': {'description': 'Major version bump detected'}
        },
        {
            'rule': 'prompt_changed_protected_path',
            'severity': 'high',
            'spec': {
                'description': 'Prompt hash changed under protected path',
                'protected_paths': ['/prompts/', '/prod/']
            }
        }
    ]
    
    with db_manager.engine.connect() as conn:
        for policy in default_policies:
            try:
                conn.execute(text("""
                    INSERT IGNORE INTO policies (rule, severity, spec) 
                    VALUES (:rule, :severity, :spec)
                """), {
                    'rule': policy['rule'],
                    'severity': policy['severity'],
                    'spec': str(policy['spec']).replace("'", '"')
                })
            except Exception as e:
                logger.warning(f"Failed to seed policy {policy['rule']}: {e}")
        
        conn.commit()
    
    logger.info("Default policies seeded")

def selftest():
    """
    Comprehensive self-test function that checks:
    - Database connection
    - Vector functions availability
    - FULLTEXT/BM25 mode
    - API keys configuration
    """
    print("🔍 ML-BOM Autopilot Self-Test")
    print("=" * 50)
    
    # Test 1: Database Connection
    print("1. Database Connection:")
    try:
        health = db_manager.health_check()
        if health["status"] == "healthy":
            print("   ✅ Database connection: OK")
            print(f"   📊 TiDB Version: {health['capabilities'].get('version', 'Unknown')}")
        else:
            print(f"   ❌ Database connection: FAILED - {health.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"   ❌ Database connection: FAILED - {e}")
        return False
    
    # Test 2: Vector Functions
    print("\n2. Vector Functions:")
    try:
        with db_manager.engine.connect() as conn:
            result = conn.execute(text("SELECT VEC_COSINE_DISTANCE('[1,2,3]', '[1,2,3]') as distance"))
            distance = result.scalar()
            if distance is not None:
                print("   ✅ Vector functions: Available")
                print(f"   📐 Test distance: {distance}")
            else:
                print("   ❌ Vector functions: Not available")
    except Exception as e:
        print(f"   ❌ Vector functions: Not available - {e}")
    
    # Test 3: FULLTEXT/BM25 Mode
    print("\n3. Search Mode:")
    global FTS_ENABLED
    if FTS_ENABLED:
        print("   ✅ Search mode: TiDB FULLTEXT")
    else:
        print("   🟡 Search mode: BM25 (app-level fallback)")
    
    # Test 4: API Keys
    print("\n4. API Keys:")
    
    # Check embedding provider
    embed_provider = config('EMBED_PROVIDER', default='openai')
    print(f"   🔧 Embedding provider: {embed_provider}")
    
    if embed_provider == 'openai':
        openai_key = config('OPENAI_API_KEY', default='')
        if openai_key and openai_key.startswith('sk-'):
            print("   ✅ OpenAI API key: Configured")
        else:
            print("   ❌ OpenAI API key: Missing or invalid")
    
    elif embed_provider == 'gemini':
        gemini_key = config('GEMINI_API_KEY', default='')
        if gemini_key and gemini_key.startswith('AIza'):
            print("   ✅ Gemini API key: Configured")
        else:
            print("   ❌ Gemini API key: Missing or invalid")
    
    # Check notification services
    slack_webhook = config('SLACK_WEBHOOK_URL', default='')
    if slack_webhook and slack_webhook.startswith('https://hooks.slack.com'):
        print("   ✅ Slack webhook: Configured")
    else:
        print("   🟡 Slack webhook: Not configured")
    
    jira_url = config('JIRA_URL', default='')
    jira_token = config('JIRA_API_TOKEN', default='')
    if jira_url and jira_token:
        print("   ✅ Jira API: Configured")
    else:
        print("   🟡 Jira API: Not configured")
    
    # Check HuggingFace token
    hf_token = config('HF_TOKEN', default='')
    if hf_token:
        print("   ✅ HuggingFace token: Configured")
    else:
        print("   🟡 HuggingFace token: Not configured")
    
    print("\n" + "=" * 50)
    print("✅ Self-test completed!")
    return True

def migration_runner():
    """CLI migration runner"""
    parser = argparse.ArgumentParser(description='ML-BOM Autopilot Database Migration Runner')
    parser.add_argument('command', choices=['up', 'selftest', 'resize-vector'], 
                       help='Migration command: up (run migrations), selftest (run diagnostics), or resize-vector (resize embedding column)')
    parser.add_argument('--dimension', type=int, choices=[768, 1536, 3072],
                       help='Target vector dimension for resize-vector command')
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = config('LOG_LEVEL', default='INFO')
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.command == 'up':
        print("🚀 Running database migrations...")
        try:
            run_migrations()
            seed_policies()
            print("✅ Migrations completed successfully!")
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            sys.exit(1)
    
    elif args.command == 'selftest':
        success = selftest()
        if not success:
            sys.exit(1)
    
    elif args.command == 'resize-vector':
        from core.db.resize_vector_migration import auto_resize_for_provider, resize_vector_column, validate_migration
        
        if args.dimension:
            # Manual dimension resize
            print(f"🚀 Resizing vector column to {args.dimension} dimensions...")
            success = resize_vector_column(args.dimension)
            if success:
                success = validate_migration(args.dimension)
        else:
            # Auto-resize based on EMBED_PROVIDER
            print("🚀 Auto-resizing vector column based on EMBED_PROVIDER...")
            success = auto_resize_for_provider()
        
        if not success:
            print("❌ Vector column resize failed")
            sys.exit(1)
        else:
            print("✅ Vector column resize completed successfully!")

if __name__ == "__main__":
    migration_runner()