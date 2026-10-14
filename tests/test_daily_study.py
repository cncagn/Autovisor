import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
import sqlite3
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from modules.daily_study import (
    DailyStudyBudget, SHANGHAI, StudyStore, account_key, course_key,
)
from modules.course_runner import CourseOutcome, _run_with_daily_budget, run_course
from modules.lesson_navigation import WISDOM_CATALOG


def snapshot(current=0, **changes):
    result = dict(currentTime=current, playbackRate=1, paused=False, ended=False,
                  seeking=False, readyState=4, source="lesson.mp4", blocked=False)
    result.update(changes)
    return result


class StudyStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'study.sqlite3'
        self.store = StudyStore(self.path)
        self.addCleanup(self.store.close)

    def test_reopen_recovers_daily_and_historical_totals(self):
        self.store.consume('a', 'c', '2026-10-13', 600, 1800)
        self.store.consume('a', 'c', '2026-10-14', 720, 1800)
        second = StudyStore(self.path)
        try:
            self.assertEqual(second.seconds('a', 'c', '2026-10-14'), 720)
            self.assertEqual(second.total('a', 'c'), 1320)
            self.assertEqual(second.history()[0][2:], ('2026-10-14', 720))
        finally:
            second.close()

    def test_accounts_courses_and_dates_have_separate_budgets(self):
        self.store.consume('a', 'c', '2026-10-14', 1799.8, 1800)
        self.assertAlmostEqual(self.store.consume('a', 'c', '2026-10-14', 1, 1800), .2)
        self.assertEqual(self.store.seconds('b', 'c', '2026-10-14'), 0)
        self.assertEqual(self.store.seconds('a', 'other', '2026-10-14'), 0)
        self.assertEqual(self.store.seconds('a', 'c', '2026-10-15'), 0)

    def test_concurrent_connections_do_not_lose_updates_or_overspend(self):
        def spend():
            connection = StudyStore(self.path)
            try:
                return sum(connection.consume('a', 'c', '2026-10-14', 100, 1800) for _ in range(10))
            finally:
                connection.close()
        with ThreadPoolExecutor(max_workers=4) as executor:
            spent = list(executor.map(lambda _: spend(), range(4)))
        self.assertEqual(sum(spent), 1800)
        self.assertEqual(self.store.seconds('a', 'c', '2026-10-14'), 1800)

    def test_bad_record_is_not_replaced_with_empty_history(self):
        path = Path(self.temp.name) / 'bad.sqlite3'
        path.write_bytes(b'not a sqlite database')
        with self.assertRaises(sqlite3.DatabaseError):
            StudyStore(path)
        self.assertEqual(path.read_bytes(), b'not a sqlite database')

    def test_invalid_charge_cannot_poison_totals(self):
        for invalid in (float('nan'), float('inf'), -1):
            with self.assertRaises(ValueError):
                self.store.consume('a', 'c', '2026-10-14', invalid, 1800)
        self.assertEqual(self.store.total('a', 'c'), 0)


class PlaybackMeterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = StudyStore(Path(self.temp.name) / 'history.sqlite3')
        self.addCleanup(self.store.close)
        self.now = datetime(2026, 10, 14, 12, tzinfo=SHANGHAI)
        self.budget = DailyStudyBudget(self.store, 'a', 'c', 30, now=lambda: self.now)

    def feed(self, state, mono, enabled=True):
        return self.budget.observe(state, enabled, mono, self.now + timedelta(seconds=mono))

    def test_only_wall_time_is_charged_at_high_playback_speed(self):
        self.feed(snapshot(0, **{'playbackRate': 1.8}), 0)
        charged = self.feed(snapshot(.9, **{'playbackRate': 1.8}), .5)
        self.assertAlmostEqual(charged, .5)

    def test_pause_buffer_overlay_seek_stall_and_gate_are_not_charged(self):
        cases = [
            (dict(paused=True), True), (dict(readyState=2), True),
            (dict(blocked=True), True), (dict(seeking=True), True),
            ({}, False),
        ]
        for changes, enabled in cases:
            self.budget.previous = None
            self.feed(snapshot(10), 0)
            state = snapshot(10.5)
            state.update(changes)
            self.assertEqual(self.feed(state, .5, enabled), 0)
        self.budget.previous = None
        self.feed(snapshot(10), 0)
        self.assertEqual(self.feed(snapshot(10), .5), 0)
        self.assertEqual(self.budget.today_seconds, 0)

    def test_forward_seek_and_rewind_are_not_minutes_of_learning(self):
        self.feed(snapshot(5), 0)
        self.assertEqual(self.feed(snapshot(50), .5), 0)
        self.assertEqual(self.feed(snapshot(1), 1), 0)
        self.assertAlmostEqual(self.feed(snapshot(1.5), 1.5), .5)

    def test_source_switch_and_sleep_gap_reset_sampling(self):
        self.feed(snapshot(5), 0)
        state = snapshot(5.5)
        state['source'] = 'other.mp4'
        self.assertEqual(self.feed(state, .5), 0)
        self.assertEqual(self.feed(snapshot(30), 30), 0)
        self.assertAlmostEqual(self.feed(snapshot(30.5), 30.5), .5)

    def test_terminal_video_sample_counts_only_remaining_playback(self):
        self.feed(snapshot(99.75), 0)
        final = snapshot(100)
        final.update(paused=True, ended=True)
        self.assertAlmostEqual(self.feed(final, .5), .25)

    def test_quota_persists_and_reopening_today_does_not_reset_it(self):
        self.store.consume('a', 'c', self.budget.day, 1799.8, 1800)
        self.feed(snapshot(0), 0)
        self.assertAlmostEqual(self.feed(snapshot(.5), .5), .2)
        self.assertTrue(self.budget.exhausted)
        reopened = DailyStudyBudget(self.store, 'a', 'c', 30, now=lambda: self.now)
        self.assertTrue(reopened.exhausted)
        self.now += timedelta(days=1)
        next_day = DailyStudyBudget(self.store, 'a', 'c', 30, now=lambda: self.now)
        self.assertFalse(next_day.exhausted)
        self.assertEqual(next_day.today_seconds, 0)

    def test_midnight_sample_is_split_between_china_calendar_dates(self):
        self.now = datetime(2026, 10, 14, 23, 59, 59, 500000, tzinfo=SHANGHAI)
        self.feed(snapshot(0), 0)
        self.assertAlmostEqual(self.feed(snapshot(1), 1), 1)
        self.assertAlmostEqual(self.store.seconds('a', 'c', '2026-10-14'), .5)
        self.assertAlmostEqual(self.store.seconds('a', 'c', '2026-10-15'), .5)

    def test_system_clock_jump_is_not_charged_as_playback(self):
        self.feed(snapshot(0), 0)
        self.assertEqual(self.budget.observe(snapshot(.5), True, .5, self.now + timedelta(hours=1)), 0)


class IdentityTests(unittest.TestCase):
    def test_explicit_profile_survives_auth_cookie_refresh(self):
        cookies = [{'name': 'CASLOGC', 'domain': '.zhihuishu.com', 'value': '{"userId":"42"}'}]
        self.assertEqual(account_key(cookies, 'account1'), account_key([], 'account1'))
        self.assertNotEqual(account_key([], 'account1'), account_key([], 'account2'))

    def test_auto_identity_uses_user_id_not_session_cookie(self):
        def cookies(session):
            return [{'name': 'CASLOGC', 'domain': '.zhihuishu.com',
                     'value': '{"userId":"42","session":"' + session + '"}'}]
        self.assertEqual(account_key(cookies('old')), account_key(cookies('new')))
        self.assertNotIn('42', account_key(cookies('old')))

    def test_unknown_or_other_site_cookie_requires_profile(self):
        for cookies in ([], [{'name': 'token', 'domain': '.zhihuishu.com', 'value': 'secret'}],
                        [{'name': 'CASLOGC', 'domain': '.evilzhihuishu.com', 'value': '{"userId":"42"}'}]):
            with self.assertRaisesRegex(ValueError, 'studyProfile'):
                account_key(cookies)

    def test_course_routes_and_display_options_share_one_quota(self):
        one = 'https://studyvideoh5.zhihuishu.com/stuStudy?recruitAndCourseId=abc'
        other = 'https://fusioncourseh5.zhihuishu.com/stuStudy/aiStudy?darkMode=1&recruitAndCourseId=abc'
        self.assertEqual(course_key(one), course_key(other))
        self.assertNotEqual(course_key(one), course_key(one.replace('abc', 'different')))


class DailyRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_quota_cancels_waiting_lesson_and_pauses_owned_video(self):
        gate = asyncio.Event()
        cancelled = asyncio.Event()

        async def wait_forever(*_args):
            gate.set()
            try:
                await asyncio.Future()
            finally:
                cancelled.set()

        page = SimpleNamespace(evaluate=AsyncMock())
        budget = SimpleNamespace(monitor=AsyncMock(return_value='daily_limit'), report=Mock(), day='2026-10-14')
        with patch('modules.course_runner._play_lessons', side_effect=wait_forever):
            result = await _run_with_daily_budget(page, WISDOM_CATALOG, object(), Mock(), gate, [], True, budget)
        self.assertIs(result, CourseOutcome.DAILY_LIMIT)
        self.assertTrue(cancelled.is_set())
        self.assertFalse(gate.is_set())
        page.evaluate.assert_awaited_once()

    async def test_storage_failure_stops_playback_instead_of_resetting_quota(self):
        gate = asyncio.Event()
        gate.set()
        page = SimpleNamespace(evaluate=AsyncMock())
        budget = SimpleNamespace(monitor=AsyncMock(side_effect=sqlite3.OperationalError('disk full')))
        async def wait_forever(*_args):
            await asyncio.Future()
        with patch('modules.course_runner._play_lessons', new=wait_forever):
            with self.assertRaises(sqlite3.OperationalError):
                await _run_with_daily_budget(page, WISDOM_CATALOG, object(), Mock(), gate, [], True, budget)
        self.assertFalse(gate.is_set())
        page.evaluate.assert_awaited_once()

    async def test_completed_course_never_clicks_or_reviews_even_if_quota_is_spent(self):
        page = SimpleNamespace(wait_for_selector=AsyncMock())
        budget = Mock(exhausted=True)
        with patch('modules.course_runner.get_filtered_class', AsyncMock(side_effect=[[], [object()]])), \
             patch('modules.course_runner._play_lessons', AsyncMock()) as play:
            result = await run_course(page, WISDOM_CATALOG, SimpleNamespace(reviewCompletedCourses=False),
                                      Mock(), asyncio.Event(), study_budget=budget)
        self.assertIs(result, CourseOutcome.COMPLETED)
        play.assert_not_awaited()
        budget.monitor.assert_not_called()

    async def test_already_spent_today_does_not_start_a_lesson(self):
        page = SimpleNamespace(wait_for_selector=AsyncMock())
        budget = Mock(exhausted=True)
        with patch('modules.course_runner.get_filtered_class', AsyncMock(return_value=[object()])), \
             patch('modules.course_runner._play_lessons', AsyncMock()) as play:
            result = await run_course(page, WISDOM_CATALOG, object(), Mock(), asyncio.Event(), study_budget=budget)
        self.assertIs(result, CourseOutcome.DAILY_LIMIT)
        play.assert_not_awaited()

    async def test_history_command_is_offline_and_does_not_require_config(self):
        import Autovisor
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'history.sqlite3'
            store = StudyStore(path)
            store.consume('account', 'course', '2026-10-14', 720, 1800)
            store.close()
            with patch.object(Autovisor, 'parse_args', return_value=SimpleNamespace(study_history=True)), \
                 patch.object(Autovisor, 'get_runtime_path', return_value=str(path)), \
                 patch.object(Autovisor.updater, 'check_for_update') as update, \
                 patch.object(Autovisor, 'main', AsyncMock()) as main, \
                 patch('builtins.print') as output:
                self.assertEqual(Autovisor.cli(), 0)
                self.assertTrue(any('12.00 分钟' in str(call) for call in output.call_args_list))
            update.assert_not_called()
            main.assert_not_awaited()
