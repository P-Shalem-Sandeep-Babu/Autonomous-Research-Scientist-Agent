import sqlite3
import os

def repair_database():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "arsa.db"))
    if not os.path.exists(db_path):
        print("Database arsa.db not found. It will be created automatically on start.")
        return

    print(f"Connecting to database at {db_path} to check schema...")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Repair research_stages table
    try:
        # Check current columns in research_stages
        cursor.execute("PRAGMA table_info(research_stages)")
        columns = [row[1] for row in cursor.fetchall()]
        
        # Add is_approved if missing
        if "is_approved" not in columns:
            print("Adding 'is_approved' column to 'research_stages' table...")
            cursor.execute("ALTER TABLE research_stages ADD COLUMN is_approved BOOLEAN DEFAULT 0")
        
        # Add user_feedback if missing
        if "user_feedback" not in columns:
            print("Adding 'user_feedback' column to 'research_stages' table...")
            cursor.execute("ALTER TABLE research_stages ADD COLUMN user_feedback TEXT")
            
        # Add reasoning_chain if missing
        if "reasoning_chain" not in columns:
            print("Adding 'reasoning_chain' column to 'research_stages' table...")
            cursor.execute("ALTER TABLE research_stages ADD COLUMN reasoning_chain JSON")
            
        print("research_stages table checked and repaired successfully.")
    except Exception as e:
        print(f"Error repairing research_stages: {e}")

    # 2. Deduplicate dataset_recommendations
    try:
        cursor.execute("""
            DELETE FROM dataset_recommendations
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM dataset_recommendations
                GROUP BY project_id, name
            )
        """)
        print("Cleaned duplicate dataset recommendations.")
    except Exception as e:
        print(f"Error deduplicating datasets: {e}")

    # 3. Deduplicate experiment_plans (keep latest per project)
    try:
        cursor.execute("""
            DELETE FROM experiment_plans
            WHERE id NOT IN (
                SELECT MAX(id)
                FROM experiment_plans
                GROUP BY project_id
            )
        """)
        print("Cleaned duplicate experiment plans.")
    except Exception as e:
        print(f"Error deduplicating plans: {e}")

    # 4. Repair users table (add compute quota, active status, billing & subscriptions if missing)
    try:
        cursor.execute("PRAGMA table_info(users)")
        u_cols = [row[1] for row in cursor.fetchall()]
        if "compute_quota_gpu_hours" not in u_cols:
            print("Adding 'compute_quota_gpu_hours' to 'users'...")
            cursor.execute("ALTER TABLE users ADD COLUMN compute_quota_gpu_hours FLOAT DEFAULT 100.0")
        if "compute_used_gpu_hours" not in u_cols:
            print("Adding 'compute_used_gpu_hours' to 'users'...")
            cursor.execute("ALTER TABLE users ADD COLUMN compute_used_gpu_hours FLOAT DEFAULT 0.0")
        if "is_active" not in u_cols:
            print("Adding 'is_active' to 'users'...")
            cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
        if "subscription_tier" not in u_cols:
            print("Adding 'subscription_tier' to 'users'...")
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_tier TEXT DEFAULT 'free'")
        if "balance_usd" not in u_cols:
            print("Adding 'balance_usd' to 'users'...")
            cursor.execute("ALTER TABLE users ADD COLUMN balance_usd FLOAT DEFAULT 25.0")
        if "token_quota" not in u_cols:
            print("Adding 'token_quota' to 'users'...")
            cursor.execute("ALTER TABLE users ADD COLUMN token_quota INTEGER DEFAULT 500000")
        if "token_used" not in u_cols:
            print("Adding 'token_used' to 'users'...")
            cursor.execute("ALTER TABLE users ADD COLUMN token_used INTEGER DEFAULT 0")
        if "stripe_customer_id" not in u_cols:
            print("Adding 'stripe_customer_id' to 'users'...")
            cursor.execute("ALTER TABLE users ADD COLUMN stripe_customer_id TEXT")
        if "mfa_enabled" not in u_cols:
            print("Adding 'mfa_enabled' to 'users'...")
            cursor.execute("ALTER TABLE users ADD COLUMN mfa_enabled BOOLEAN DEFAULT 0")
        if "mfa_secret" not in u_cols:
            print("Adding 'mfa_secret' to 'users'...")
            cursor.execute("ALTER TABLE users ADD COLUMN mfa_secret TEXT")
        if "password_reset_token" not in u_cols:
            print("Adding 'password_reset_token' to 'users'...")
            cursor.execute("ALTER TABLE users ADD COLUMN password_reset_token TEXT")
        if "password_reset_expires_at" not in u_cols:
            print("Adding 'password_reset_expires_at' to 'users'...")
            cursor.execute("ALTER TABLE users ADD COLUMN password_reset_expires_at TIMESTAMP")
    except Exception as e:
        print(f"Error repairing users table: {e}")

    # 4b. Repair projects table (add checkpointing, current_stage, and heartbeat columns)
    try:
        cursor.execute("PRAGMA table_info(projects)")
        p_cols = [row[1] for row in cursor.fetchall()]
        if "current_stage" not in p_cols:
            print("Adding 'current_stage' to 'projects'...")
            cursor.execute("ALTER TABLE projects ADD COLUMN current_stage TEXT DEFAULT 'literature'")
        if "checkpoint_data" not in p_cols:
            print("Adding 'checkpoint_data' to 'projects'...")
            cursor.execute("ALTER TABLE projects ADD COLUMN checkpoint_data JSON")
        if "last_heartbeat" not in p_cols:
            print("Adding 'last_heartbeat' to 'projects'...")
            cursor.execute("ALTER TABLE projects ADD COLUMN last_heartbeat TIMESTAMP")
    except Exception as e:
        print(f"Error repairing projects table: {e}")

    # 4c. Ensure billing_transactions table exists
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS billing_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                amount_usd FLOAT NOT NULL,
                transaction_type TEXT NOT NULL,
                status TEXT DEFAULT 'completed',
                description TEXT NOT NULL,
                reference_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_billing_user_id ON billing_transactions (user_id)")
    except Exception as e:
        print(f"Error creating billing_transactions table: {e}")

    # 4d. Ensure document_embeddings table exists
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS document_embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                collection_name TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                text TEXT NOT NULL,
                metadata_json JSON,
                embedding_json JSON NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_embeddings_collection ON document_embeddings (collection_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_embeddings_doc_id ON document_embeddings (doc_id)")
    except Exception as e:
        print(f"Error creating document_embeddings table: {e}")

    # 4e. Ensure immutable audit_logs table exists
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER REFERENCES projects(id) ON DELETE CASCADE,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                action TEXT NOT NULL,
                resource TEXT,
                details JSON,
                ip_address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_audit_project_id ON audit_logs (project_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_audit_user_id ON audit_logs (user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_audit_action ON audit_logs (action)")
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_audit_created_at ON audit_logs (created_at)")
    except Exception as e:
        print(f"Error creating audit_logs table: {e}")

    # 5. Ensure api_key_configs table exists and seed if empty
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_key_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider TEXT NOT NULL,
                model_name TEXT NOT NULL,
                masked_key TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_used TIMESTAMP
            )
        """)
        cursor.execute("SELECT COUNT(*) FROM api_key_configs")
        key_count = cursor.fetchone()[0]
        if key_count == 0:
            print("Seeding initial API key configurations...")
            cursor.execute("""
                INSERT INTO api_key_configs (provider, model_name, masked_key, status)
                VALUES 
                ('Gemini Pro (Google)', 'gemini-3.1-flash-lite', 'AIza••••••••9xK2', 'active'),
                ('OpenAI GPT-4o', 'gpt-4o-2026', 'sk-proj-••••••••8wM1', 'active'),
                ('LM Studio Local Engine', 'qwen-2.5-7b', 'http://localhost:1234/v1', 'active')
            """)
    except Exception as e:
        print(f"Error initializing api_key_configs: {e}")

    # 6. Ensure system_compute_configs table exists and seed if empty
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_compute_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                active_gpus TEXT DEFAULT '1x NVIDIA A100 (80GB)',
                allocated_cpu_cores INTEGER DEFAULT 16,
                memory_limit_gb INTEGER DEFAULT 64,
                utilization_pct INTEGER DEFAULT 45,
                scheduler_status TEXT DEFAULT 'online',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("SELECT COUNT(*) FROM system_compute_configs")
        compute_count = cursor.fetchone()[0]
        if compute_count == 0:
            print("Seeding initial System Compute configuration...")
            cursor.execute("""
                INSERT INTO system_compute_configs (active_gpus, allocated_cpu_cores, memory_limit_gb, utilization_pct, scheduler_status)
                VALUES ('1x NVIDIA A100 (80GB)', 16, 64, 45, 'online')
            """)
    except Exception as e:
        print(f"Error initializing system_compute_configs: {e}")

    conn.commit()
    conn.close()
    print("Database check and repair complete.")

if __name__ == "__main__":
    repair_database()

