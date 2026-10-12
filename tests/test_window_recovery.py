from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from modules import utils


class WindowError(Exception):
    pass


class WindowRecoveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_stale_handle_is_reacquired_before_display(self):
        stale, fresh = Mock(), Mock()
        stale.moveTo.side_effect = WindowError("1400: invalid window handle")
        with patch.object(utils, "gw", SimpleNamespace(PyGetWindowException=WindowError)), \
                patch.object(utils, "logger", Mock()), \
                patch.object(utils, "get_browser_window", AsyncMock(side_effect=[stale, fresh])) as get:
            self.assertTrue(await utils._change_browser_window(object(), visible=True))
        self.assertEqual(get.await_count, 2)
        fresh.moveTo.assert_called_once_with(100, 100)

    async def test_persistent_invalid_handle_is_bounded_and_nonfatal(self):
        stale = Mock()
        stale.hide.side_effect = WindowError("1400: invalid window handle")
        logger = Mock()
        with patch.object(utils, "gw", SimpleNamespace(PyGetWindowException=WindowError)), \
                patch.object(utils, "logger", logger), \
                patch.object(utils, "get_browser_window", AsyncMock(return_value=stale)) as get:
            self.assertFalse(await utils._change_browser_window(object(), visible=False))
        self.assertEqual(get.await_count, 2)
        logger.warn.assert_called_once()

    async def test_missing_window_is_nonfatal(self):
        with patch.object(utils, "logger", Mock()), \
                patch.object(utils, "get_browser_window", AsyncMock(return_value=None)):
            self.assertFalse(await utils._change_browser_window(object(), visible=False))
