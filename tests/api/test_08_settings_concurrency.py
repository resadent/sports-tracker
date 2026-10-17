"""The dashboard fetches settings and series concurrently on first login."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from sports_tracker.db.models.user_settings import UserSettings
from sports_tracker.db.repositories.user_settings_repo import UserSettingsRepository


def test_concurrent_first_settings_reads_reuse_single_row(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'settings-race.sqlite'}")
    UserSettings.__table__.create(engine)
    both_selected = Barrier(2)

    class SimultaneousSession(Session):
        def scalar(self, *args, **kwargs):
            result = super().scalar(*args, **kwargs)
            if not getattr(self, "selected", False):
                self.selected = True
                assert result is None
                both_selected.wait(timeout=5)
            return result

    def read_settings():
        with SimultaneousSession(engine) as session:
            row = UserSettingsRepository(session).get_or_create(1)
            return row.id, row.weight_unit, row.waist_unit

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: read_settings(), range(2)))
    assert results[0] == results[1]
    assert results[0][1:] == ("kg", "cm")
    with Session(engine) as session:
        assert len(list(session.scalars(select(UserSettings)))) == 1
    engine.dispose()
