"""
Test bootstrap: add project paths once for all tests.
"""

import pytest

from path_bootstrap import bootstrap_tests

bootstrap_tests()


@pytest.fixture
def camera():
    """Provide a simulated camera for tests that expect a camera fixture."""
    from drivers.camera import create_camera

    cam = create_camera(simulation=True)
    try:
        yield cam
    finally:
        try:
            cam.close()
        except Exception:
            pass
