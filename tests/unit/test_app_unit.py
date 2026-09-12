import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.app import _csrf_token_refresh_loop, _refresh_csrf_token, app, main


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@patch("app.app.pesu_academy.authenticate")
def test_authenticate_validation_error(mock_authenticate, client, caplog):
    mock_authenticate.return_value = {
        "status": True,
        "message": "Login successful",
        "profile": "this should cause validation error",
    }
    payload = {"username": "testuser", "password": "testpass", "profile": False}
    with caplog.at_level("DEBUG"):
        response = client.post("/authenticate", json=payload)
    assert response.status_code == 500
    data = response.json()
    assert "Internal Server Error" in data["message"]
    assert "Validation error on ResponseModel" in caplog.text


@patch("app.app.pesu_academy.authenticate")
def test_authenticate_general_exception(mock_authenticate, client):
    mock_authenticate.side_effect = Exception("Test exception")
    payload = {"username": "testuser", "password": "testpass", "profile": False}
    response = client.post("/authenticate", json=payload)
    assert response.status_code == 500
    data = response.json()
    assert "Internal Server Error" in data["message"]


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
@patch("app.app._refresh_csrf_token")
async def test_csrf_token_refresh_loop_logs_exception_on_failure(mock_refresh, mock_sleep, caplog):
    mock_refresh.side_effect = RuntimeError("Simulated CSRF refresh failure")
    mock_sleep.side_effect = asyncio.CancelledError

    with caplog.at_level("ERROR"):
        with pytest.raises(asyncio.CancelledError):
            await _csrf_token_refresh_loop()

    assert "Failed to refresh unauthenticated CSRF token in the background." in caplog.text


@patch("app.app.argparse.ArgumentParser.parse_args")
@patch("app.app.logging.basicConfig")
@patch("app.app.uvicorn.run")
def test_main_function_default_args(mock_run, mock_logging, mock_parse_args):
    mock_args = MagicMock()
    mock_args.host = "0.0.0.0"
    mock_args.port = 5000
    mock_args.debug = False
    mock_parse_args.return_value = mock_args

    main()

    mock_logging.assert_called_once()
    mock_run.assert_called_once_with("app.app:app", host="0.0.0.0", port=5000, reload=False)


@patch("app.app.argparse.ArgumentParser.parse_args")
@patch("app.app.logging.basicConfig")
@patch("app.app.uvicorn.run")
def test_main_function_debug_mode(mock_run, mock_logging, mock_parse_args):
    mock_args = MagicMock()
    mock_args.host = "127.0.0.1"
    mock_args.port = 8000
    mock_args.debug = True
    mock_parse_args.return_value = mock_args

    main()

    mock_logging.assert_called_once()
    mock_run.assert_called_once_with("app.app:app", host="127.0.0.1", port=8000, reload=True)


@pytest.mark.asyncio
@patch("app.app.pesu_academy.prefetch_client_with_csrf_token", new_callable=AsyncMock)
async def test_refresh_csrf_token_delegates_to_pesu_academy(mock_prefetch, caplog):
    """The refresh helper must delegate to PESUAcademy and report success."""
    with caplog.at_level("INFO"):
        await _refresh_csrf_token()

    mock_prefetch.assert_awaited_once()
    assert "Unauthenticated CSRF token refreshed successfully." in caplog.text


@pytest.fixture
def mocked_pesu_client():
    """A TestClient whose PESUAcademy singleton is mocked, so lifespan makes no network calls."""
    with patch("app.app.pesu_academy", new_callable=AsyncMock) as mock_pesu:
        mock_pesu.authenticate.return_value = {
            "status": True,
            "message": "Login successful.",
        }
        with TestClient(app, raise_server_exceptions=False) as client:
            yield client, mock_pesu


def test_authenticate_does_not_trigger_additional_prefetch(mocked_pesu_client):
    """The endpoint must not kick off its own CSRF prefetch; app/pesu.py already does one."""
    client, mock_pesu = mocked_pesu_client
    # Snapshot rather than assert an absolute count: lifespan startup and the periodic
    # refresh loop both legitimately prefetch, and their scheduling is not deterministic.
    before = mock_pesu.prefetch_client_with_csrf_token.await_count

    response = client.post("/authenticate", json={"username": "user", "password": "pass"})

    assert response.status_code == 200
    # Starlette runs background tasks before TestClient returns, so any endpoint-level
    # prefetch would already be counted here.
    assert mock_pesu.prefetch_client_with_csrf_token.await_count == before
