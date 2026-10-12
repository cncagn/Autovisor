"""Clock-driven regressions: rewinds keep moving, frozen playback still fails."""
from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from modules.course_playback import learn_lesson, review_lesson
from modules.lesson_navigation import WISDOM_CATALOG


class PlaybackStallTests(unittest.IsolatedAsyncioTestCase):
    async def simulate(self, times, progresses, review=False):
        clock = SimpleNamespace(now=0)

        async def tick(_seconds):
            clock.now += 30

        page = SimpleNamespace(wait_for_timeout=AsyncMock(), evaluate=AsyncMock())
        logger = Mock()
        with ExitStack() as stack:
            replacements = {
                "_wait_for_duration": AsyncMock(return_value=(535, 0)),
                "has_visible_verification": AsyncMock(return_value=False),
                "has_visible_element": AsyncMock(return_value=False),
                "get_video_attr": AsyncMock(side_effect=times),
                "lesson_progress": AsyncMock(side_effect=progresses),
                "wait_for_lesson_completion": AsyncMock(return_value=True),
                "show_course_progress": Mock(),
                "run_on": AsyncMock(),
                "time.monotonic": lambda: clock.now,
                "time.time": lambda: clock.now,
                "asyncio.sleep": tick,
            }
            for name, value in replacements.items():
                stack.enter_context(patch("modules.course_playback." + name, value))
            config = SimpleNamespace(limitMaxTime=0)
            if review:
                result = await review_lesson(page, 0, 0, config, logger)
            else:
                result = await learn_lesson(
                    page, 0, 0, object(), WISDOM_CATALOG, config, logger
                )
        return result, logger

    async def test_learning_rewind_does_not_require_old_high_water_mark(self):
        result, logger = await self.simulate(
            [308, 52, 106, 160, 225, 280], [60] * 6 + [100]
        )
        self.assertTrue(result[1])
        logger.warn.assert_not_called()

    async def test_review_rewind_does_not_require_old_high_water_mark(self):
        result, logger = await self.simulate(
            [308, 52, 106, 160, 225, 280, 535], [], review=True
        )
        self.assertTrue(result[1])
        logger.warn.assert_not_called()

    async def test_frozen_learning_still_stops_after_120_seconds(self):
        result, logger = await self.simulate([150] * 5, [60] * 5)
        self.assertEqual(result, (0, False, False))
        self.assertIn("120", logger.warn.call_args.args[0])

    async def test_frozen_review_still_stops_after_120_seconds(self):
        result, logger = await self.simulate([150] * 5, [], review=True)
        self.assertEqual(result, (0, False, False))
        self.assertIn("120", logger.warn.call_args.args[0])
