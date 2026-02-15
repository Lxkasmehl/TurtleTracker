"""
Pytest configuration and fixtures for backend integration tests.
Uses a stub for manager_service so the real TurtleManager (and its background thread) never loads.
Routes get the fake_manager from the stub; no real backend/data is touched.
"""

import sys
import threading
import pytest
from unittest.mock import patch

# Stub manager_service so the real module (and its background TurtleManager thread) never loads.
# Otherwise the thread would overwrite manager with the real instance and tests would see backend/data.
_manager_service_stub = type(sys)("manager_service")
_manager_service_stub.manager = None
_manager_service_stub.manager_ready = threading.Event()
_manager_service_stub.manager_ready.set()


def _stub_get_sheets_service():
    """Stub for get_sheets_service so routes can import it; returns None so Sheets code paths are no-ops."""
    return None


_manager_service_stub.get_sheets_service = _stub_get_sheets_service
# Install before any test or app code imports manager_service (conftest loads first).
sys.modules["services.manager_service"] = _manager_service_stub


@pytest.fixture
def fake_manager(tmp_path):
    """Fake TurtleManager using a temporary directory (tmp_path is pytest built-in)."""
    from tests.fake_turtle_manager import FakeTurtleManager
    base = str(tmp_path / "data")
    manager = FakeTurtleManager(base_dir=base)
    yield manager


@pytest.fixture
def manager_ready_event():
    """Event that is already set so manager_ready.wait() returns immediately."""
    ev = threading.Event()
    ev.set()
    return ev


@pytest.fixture
def admin_auth():
    """Make get_user_from_request return admin so require_admin passes."""

    def fake_get_user():
        return True, {"role": "admin", "sub": "test-admin"}, None

    return fake_get_user


@pytest.fixture
def client(fake_manager, manager_ready_event, admin_auth):
    """Flask test client with stubbed manager and patched auth."""
    _manager_service_stub.manager = fake_manager
    _manager_service_stub.manager_ready = manager_ready_event
    with patch("auth.get_user_from_request", admin_auth):
        from app import app
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c
