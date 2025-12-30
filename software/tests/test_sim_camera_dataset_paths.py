from pathlib import Path

import simulation.camera_simulated as cam_sim


def test_no_absolute_path_literal():
    text = Path(cam_sim.__file__).read_text()
    assert "/Users/" not in text
    assert "droplet_AInalysis" not in text


def test_env_var_priority(tmp_path, monkeypatch):
    # Create fake dataset structure
    base = tmp_path / "dataset"
    (base / "backgrounds").mkdir(parents=True)
    (base / "droplets").mkdir(parents=True)

    monkeypatch.setenv("RIO_DROPLET_TESTDATA_DIR", str(base))
    resolved = cam_sim._resolve_droplet_dataset_base(repo_root=tmp_path)
    assert resolved == base


def test_repo_relative_fallback(tmp_path, monkeypatch):
    repo_root = tmp_path
    fallback = repo_root / "software" / "tests" / "data" / "droplet"
    (fallback / "backgrounds").mkdir(parents=True)
    (fallback / "droplets").mkdir(parents=True)

    monkeypatch.delenv("RIO_DROPLET_TESTDATA_DIR", raising=False)
    resolved = cam_sim._resolve_droplet_dataset_base(repo_root=repo_root)
    assert resolved == fallback


def test_no_dataset_returns_none(tmp_path, monkeypatch):
    repo_root = tmp_path
    monkeypatch.delenv("RIO_DROPLET_TESTDATA_DIR", raising=False)
    resolved = cam_sim._resolve_droplet_dataset_base(repo_root=repo_root)
    assert resolved is None
