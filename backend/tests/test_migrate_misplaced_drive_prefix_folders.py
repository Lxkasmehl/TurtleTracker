"""Tests for migrate_misplaced_drive_prefix_folders.py (no turtle_manager import)."""

import os

from migrate_misplaced_drive_prefix_folders import _collect_moves, main


def _mkdir_turtle(path: str) -> None:
    os.makedirs(os.path.join(path, "plastron"), exist_ok=True)


def test_collect_moves_nested_cpbs(tmp_path):
    data = tmp_path / "data"
    wrong = data / "CPBS" / "NW of Geo 2" / "F233"
    _mkdir_turtle(str(wrong))
    moves, conflicts = _collect_moves(str(data), None)
    assert not conflicts
    assert len(moves) == 1
    _key, src, dest = moves[0]
    assert src.replace("\\", "/").endswith("CPBS/NW of Geo 2/F233")
    assert dest.replace("\\", "/").endswith("NebraskaCPBS/CPBS/F233")


def test_collect_moves_conflict_when_dest_nonempty(tmp_path):
    data = tmp_path / "data"
    src = data / "CPBS" / "x" / "F233"
    _mkdir_turtle(str(src))
    dest = data / "NebraskaCPBS" / "CPBS" / "F233"
    _mkdir_turtle(str(dest))
    (dest / "plastron" / "note.txt").write_text("x", encoding="utf-8")
    moves, conflicts = _collect_moves(str(data), None)
    assert not moves
    assert len(conflicts) == 1
    assert "CONFLICT" in conflicts[0]


def test_apply_moves_and_prunes(tmp_path):
    data = tmp_path / "data"
    wrong = data / "CPBS" / "SiteA" / "F233"
    _mkdir_turtle(str(wrong))
    rc = main(["--data-root", str(data), "--apply"])
    assert rc == 0
    assert not wrong.exists()
    assert (data / "NebraskaCPBS" / "CPBS" / "F233" / "plastron").is_dir()
    assert not (data / "CPBS" / "SiteA").exists()


def test_only_filter(tmp_path):
    data = tmp_path / "data"
    _mkdir_turtle(str(data / "CPBS" / "a" / "F001"))
    _mkdir_turtle(str(data / "Lawrence" / "b" / "F002"))
    moves_all, _ = _collect_moves(str(data), None)
    names = {os.path.basename(m[1]) for m in moves_all}
    assert names == {"F001", "F002"}
    moves_cpbs, _ = _collect_moves(str(data), ["CPBS"])
    assert len(moves_cpbs) == 1
    assert os.path.basename(moves_cpbs[0][1]) == "F001"


def test_apply_exit_1_when_stray_file_remains(tmp_path):
    """A non-turtle file left under data/CPBS must be reported; exit code 1."""
    data = tmp_path / "data"
    wrong = data / "CPBS" / "SiteA" / "F233"
    _mkdir_turtle(str(wrong))
    (data / "CPBS" / "README.txt").write_text("x", encoding="utf-8")
    rc = main(["--data-root", str(data), "--apply"])
    assert rc == 1
    assert (data / "NebraskaCPBS" / "CPBS" / "F233" / "plastron").is_dir()
    assert (data / "CPBS" / "README.txt").exists()
