from app.core.database import engine, Base, SessionLocal
from app.models.models import User
from app.core.security import get_password_hash

def init_db():
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Check if users already exist
        admin = db.query(User).filter(User.email == "admin@arsa.ai").first()
        if not admin:
            print("Seeding default users...")
            
            # Admin User
            admin_user = User(
                email="admin@arsa.ai",
                hashed_password=get_password_hash("password123"),
                full_name="Admin Charlie",
                role="administrator"
            )
            db.add(admin_user)
            
            # Researcher User
            researcher_user = User(
                email="researcher@arsa.ai",
                hashed_password=get_password_hash("password123"),
                full_name="Dr. Alice Researcher",
                role="researcher"
            )
            db.add(researcher_user)
            
            # Supervisor User
            supervisor_user = User(
                email="supervisor@arsa.ai",
                hashed_password=get_password_hash("password123"),
                full_name="Prof. Bob Supervisor",
                role="supervisor"
            )
            db.add(supervisor_user)
            
            db.commit()
            print("Database initialized and seeded successfully!")
        else:
            print("Database already seeded.")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
