from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sports_tracker.settings import settings
from sports_tracker.db.models.muscle import Muscle
from sports_tracker.db.models.exercise import Exercise

def seed_database():
    engine = create_engine(str(settings.settings.DATABASE_URL))
    SessionLocal = sessionmaker(bind=engine)
    
    with SessionLocal() as db:
        # 1. Create the Muscle instance
        quadriceps = Muscle(name="Quadriceps")
        
        # 2. Create the Exercise instance and assign the muscle
        quad_extension = Exercise(
            name="Quadriceps Extension", 
            muscles=[quadriceps]
        )
        
        # 3. Add to the session and commit.
        # SQLAlchemy automatically cascades this: it inserts into `muscles`, `exercises`, and `exercise_muscle`.
        db.add(quad_extension)
        db.commit()

if __name__ == "__main__":
    seed_database()