from __future__ import annotations

from pathlib import Path

from app.storage import SqliteStorage


def test_sqlite_save_latest_recent(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    st = SqliteStorage(str(db))

    st.save("d1", {"n": 1})
    st.save("d1", {"n": 2})

    latest = st.get_latest("d1")
    assert latest is not None
    assert latest.payload == {"n": 2}

    recent = st.get_recent("d1", 10)
    assert len(recent) == 2
    assert recent[0].payload == {"n": 2}
    assert recent[1].payload == {"n": 1}


def test_sqlite_get_recent_limit(tmp_path: Path) -> None:
    st = SqliteStorage(str(tmp_path / "x.db"))
    for i in range(5):
        st.save("d", {"i": i})
    recent = st.get_recent("d", 2)
    assert [m.payload["i"] for m in recent] == [4, 3]
