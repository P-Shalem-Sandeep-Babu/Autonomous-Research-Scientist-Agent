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

    conn.commit()
    conn.close()
    print("Database check and repair complete.")

if __name__ == "__main__":
    repair_database()
