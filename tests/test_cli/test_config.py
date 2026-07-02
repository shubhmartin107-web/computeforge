from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from typer.testing import CliRunner

from computeforge.cli.app import app

runner = CliRunner()


def test_config_show():
    result = runner.invoke(app, ["config", "show"])
    assert result.exit_code == 0
    assert "ComputeForge Configuration" in result.stdout
    assert "browser" in result.stdout


def test_config_set():
    with TemporaryDirectory() as tmpdir:
        with patch("pathlib.Path.home", return_value=Path(tmpdir)):
            result = runner.invoke(
                app, ["config", "set", "--key", "theme", "--value", "dark"]
            )
    assert result.exit_code == 0
    assert "Config saved" in result.stdout


def test_config_set_overwrite():
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".computeforge" / "config.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text('{"theme": "light"}')
        assert config_path.exists()

        with patch("pathlib.Path.home", return_value=Path(tmpdir)):
            result = runner.invoke(
                app, ["config", "set", "--key", "theme", "--value", "dark"]
            )
        assert result.exit_code == 0
        assert "Config saved" in result.stdout
        import json
        data = json.loads(config_path.read_text())
        assert data["theme"] == "dark"


def test_config_set_missing_args():
    result = runner.invoke(app, ["config", "set"])
    assert result.exit_code != 0
    assert "Error" in result.stdout


def test_config_reset():
    with TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".computeforge" / "config.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text('{"theme": "dark"}')
        assert config_path.exists()

        with patch("pathlib.Path.home", return_value=Path(tmpdir)):
            result = runner.invoke(app, ["config", "reset"])

        assert result.exit_code == 0
        assert "reset to defaults" in result.stdout.lower()
        assert not config_path.exists()


def test_config_caps():
    result = runner.invoke(app, ["config", "caps"])
    assert result.exit_code == 0
    assert "Capabilities" in result.stdout
    assert "browser.navigate" in result.stdout


def test_config_policies():
    result = runner.invoke(app, ["config", "policies"])
    assert result.exit_code == 0
    assert "Default Policies" in result.stdout or "Policies" in result.stdout


def test_config_unknown_action():
    result = runner.invoke(app, ["config", "unknown"])
    assert result.exit_code != 0
    assert "Unknown action" in result.stdout
