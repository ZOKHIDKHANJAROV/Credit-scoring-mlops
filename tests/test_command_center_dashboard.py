from pathlib import Path


def test_command_center_dashboard_asset_exists():
    dashboard = Path(__file__).resolve().parents[1] / "ai_engineering" / "dashboard" / "index.html"
    content = dashboard.read_text(encoding="utf-8")

    assert "Command Center" in content
    assert "/api/v1/command-center/overview" in content
    assert "Authorization" in content
    assert "setInterval(refresh,15000)" in content


def test_command_center_dashboard_is_served_by_api():
    service = Path(__file__).resolve().parents[1] / "ai_engineering" / "api" / "agent_service.py"
    content = service.read_text(encoding="utf-8")

    assert "from fastapi.staticfiles import StaticFiles" in content
    assert 'app.mount(\n    "/command-center"' in content
    assert 'StaticFiles(directory=Path(__file__).resolve().parents[1] / "dashboard", html=True)' in content
