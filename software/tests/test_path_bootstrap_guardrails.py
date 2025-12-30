from pathlib import Path


def test_no_scattered_sys_path_inserts():
    """
    Guardrail: allow sys.path.insert only in path_bootstrap.py (and tools explicitly exempted).
    Beginners should not need per-file path hacks; bootstrap handles imports.
    """

    repo_root = Path(__file__).resolve().parents[1]
    whitelist = {
        repo_root / "path_bootstrap.py",
        repo_root / "software" / "path_bootstrap.py",  # in case of alt resolution
    }
    exempt_dirs = {
        repo_root / "droplet-detection",  # CLI/benchmark tools (left as-is for now)
    }

    offenders = []
    for py in repo_root.rglob("*.py"):
        if py.name == "test_path_bootstrap_guardrails.py":
            continue
        if any(str(py).startswith(str(ex)) for ex in exempt_dirs):
            continue
        if py in whitelist:
            continue
        text = py.read_text()
        if "sys.path.insert" in text:
            offenders.append(py)

    assert not offenders, f"Unexpected sys.path.insert found in: {offenders}"


def test_smoke_imports_with_bootstrap():
    """
    Smoke-check that key modules import under bootstrap (conftest applies bootstrap_tests).
    Avoids hardware init by importing controllers/web layers only.
    """

    import controllers.flow_web  # noqa: F401
    import controllers.camera  # noqa: F401
    import controllers.strobe_cam  # noqa: F401
    import flow_controller  # noqa: F401
    import view_model  # noqa: F401
    import routes  # noqa: F401
