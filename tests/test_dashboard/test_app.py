from __future__ import annotations

import re
from unittest.mock import AsyncMock, MagicMock, patch

from computeforge.dashboard.app import create_dashboard, launch_dashboard

_APP_TAB_LABELS = []
with open("/home/synapsex/computeforge/src/computeforge/dashboard/app.py") as _f:
    for _line in _f:
        _m = re.search(r'gr\.Tab\(\"(.+?)\"\)', _line)
        if _m:
            _APP_TAB_LABELS.append(_m.group(1))


class TestCreateDashboard:
    @patch("computeforge.dashboard.app.gr")
    def test_create_dashboard_uses_provided_storage(self, mock_gr, mock_storage):
        mock_gr.Blocks.return_value.__enter__.return_value = MagicMock()
        mock_gr.Blocks.return_value.__exit__ = MagicMock()
        mock_gr.Tabs.return_value.__enter__.return_value = MagicMock()
        mock_gr.Tabs.return_value.__exit__ = MagicMock()
        mock_gr.Tab.return_value.__enter__.return_value = MagicMock()
        mock_gr.Tab.return_value.__exit__ = MagicMock()
        mock_gr.HTML = MagicMock()
        mock_gr.Markdown = MagicMock()
        mock_gr.Button = MagicMock()
        mock_gr.Textbox = MagicMock()
        mock_gr.Dataframe = MagicMock()
        mock_gr.State = MagicMock()
        mock_gr.Slider = MagicMock()
        mock_gr.Image = MagicMock()
        mock_gr.Checkbox = MagicMock()
        mock_gr.Dropdown = MagicMock()

        dashboard = create_dashboard(storage=mock_storage)

        mock_storage.connect.assert_called_once()
        assert dashboard is not None

    @patch("computeforge.dashboard.app.gr")
    def test_create_dashboard_creates_five_tabs(self, mock_gr, mock_storage):
        mock_gr.Blocks.return_value.__enter__.return_value = MagicMock()
        mock_gr.Blocks.return_value.__exit__ = MagicMock()
        mock_gr.Tabs.return_value.__enter__.return_value = MagicMock()
        mock_gr.Tabs.return_value.__exit__ = MagicMock()
        mock_gr.Tab.return_value.__enter__.return_value = MagicMock()
        mock_gr.Tab.return_value.__exit__ = MagicMock()
        mock_gr.HTML = MagicMock()
        mock_gr.Markdown = MagicMock()
        mock_gr.Button = MagicMock()
        mock_gr.Textbox = MagicMock()
        mock_gr.Dataframe = MagicMock()
        mock_gr.State = MagicMock()
        mock_gr.Slider = MagicMock()
        mock_gr.Image = MagicMock()
        mock_gr.Checkbox = MagicMock()
        mock_gr.Dropdown = MagicMock()

        create_dashboard(storage=mock_storage)

        actual_calls = [call[0][0] for call in mock_gr.Tab.call_args_list]
        assert len(actual_calls) == 5
        assert actual_calls == _APP_TAB_LABELS, f"Tab labels mismatch: {actual_calls} != {_APP_TAB_LABELS}"

    @patch("computeforge.dashboard.app.gr")
    @patch("computeforge.dashboard.app.StorageBackend")
    def test_create_dashboard_without_storage_creates_new(self, mock_sb_cls, mock_gr):
        instance = mock_sb_cls.return_value
        instance.connect = AsyncMock()
        mock_gr.Blocks.return_value.__enter__.return_value = MagicMock()
        mock_gr.Blocks.return_value.__exit__ = MagicMock()
        mock_gr.Tabs.return_value.__enter__.return_value = MagicMock()
        mock_gr.Tabs.return_value.__exit__ = MagicMock()
        mock_gr.Tab.return_value.__enter__.return_value = MagicMock()
        mock_gr.Tab.return_value.__exit__ = MagicMock()
        mock_gr.HTML = MagicMock()
        mock_gr.Markdown = MagicMock()
        mock_gr.Button = MagicMock()
        mock_gr.Textbox = MagicMock()
        mock_gr.Dataframe = MagicMock()
        mock_gr.State = MagicMock()
        mock_gr.Slider = MagicMock()
        mock_gr.Image = MagicMock()
        mock_gr.Checkbox = MagicMock()
        mock_gr.Dropdown = MagicMock()

        create_dashboard(storage=None)

        mock_sb_cls.assert_called_once()

    @patch("computeforge.dashboard.app.gr")
    def test_launch_dashboard_calls_launch_with_expected_params(self, mock_gr, mock_storage):
        mock_blocks = MagicMock()
        mock_gr.Blocks.return_value.__enter__.return_value = mock_blocks
        mock_gr.Blocks.return_value.__exit__ = MagicMock()
        mock_gr.Tabs.return_value.__enter__.return_value = MagicMock()
        mock_gr.Tabs.return_value.__exit__ = MagicMock()
        mock_gr.Tab.return_value.__enter__.return_value = MagicMock()
        mock_gr.Tab.return_value.__exit__ = MagicMock()
        mock_gr.HTML = MagicMock()
        mock_gr.Markdown = MagicMock()
        mock_gr.Button = MagicMock()
        mock_gr.Textbox = MagicMock()
        mock_gr.Dataframe = MagicMock()
        mock_gr.State = MagicMock()
        mock_gr.Slider = MagicMock()
        mock_gr.Image = MagicMock()
        mock_gr.Checkbox = MagicMock()
        mock_gr.Dropdown = MagicMock()
        mock_gr.themes = MagicMock()
        mock_gr.themes.Soft.return_value = MagicMock()
        mock_gr.themes.GoogleFont.return_value = MagicMock()

        launch_dashboard(storage=mock_storage, host="0.0.0.0", port=7890, share=True, debug=True)

        mock_blocks.launch.assert_called_once()
        launch_kwargs = mock_blocks.launch.call_args[1]
        assert launch_kwargs["server_name"] == "0.0.0.0"
        assert launch_kwargs["server_port"] == 7890
        assert launch_kwargs["share"] is True
        assert launch_kwargs["debug"] is True
