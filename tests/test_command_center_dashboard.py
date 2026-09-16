from pathlib import Path


def test_command_center_dashboard_asset_exists():
    dashboard = Path(__file__).resolve().parents[1] / "ai_engineering" / "dashboard" / "index.html"
    content = dashboard.read_text(encoding="utf-8")

    assert "Command Center" in content
    assert "/api/v1/command-center/overview" in content
    assert "Authorization" in content
    assert "setInterval(refresh,15000)" in content
