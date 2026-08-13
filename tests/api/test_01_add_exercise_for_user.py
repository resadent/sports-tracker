from __future__ import annotations

from sports_tracker.db.models.user import User
from sports_tracker.db.models.session import Session
from sports_tracker.db.models.exercise import Exercise
from sports_tracker.db.models.muscle import Muscle
from sports_tracker.db.models.workout_set import WorkoutSet


def test_add_session_with_quad_extension(db_session):
    # 1. Create a User
    user = User(email="lifter@example.com", hashed_password="not-a-real-hash")
    
    # 2. Create a Session assigned to the User
    session = Session(name="Leg Day", user=user)
    
    # 3. Create the Muscle and Exercise
    quadriceps = Muscle(name="Quadriceps")
    quad_ext = Exercise(name="Quadriceps Extension", muscles=[quadriceps])
    
    # 4. Link the Session and Exercise using a WorkoutSet
    workout_set = WorkoutSet(session=session, exercise=quad_ext, reps=12, weight=60.0)
    
    # Add the top-level objects to the session; SQLAlchemy cascades will handle the rest
    db_session.add(user)
    db_session.add(workout_set)
    db_session.commit()
    
    # 5. Query back from the database and assert relationships
    queried_session = db_session.query(Session).filter_by(name="Leg Day").first()
    
    assert queried_session is not None
    assert queried_session.user.email == "lifter@example.com"
    assert len(queried_session.workout_sets) == 1
    
    queried_exercise = queried_session.workout_sets[0].exercise
    assert queried_exercise.name == "Quadriceps Extension"
    assert len(queried_exercise.muscles) == 1
    assert queried_exercise.muscles[0].name == "Quadriceps"