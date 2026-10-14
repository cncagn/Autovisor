"""Browser regressions for nested Fusion rows, using an offline HTML fixture.

Install Chromium with ``uv run playwright install chromium``. To use an existing
Chrome installation locally, set AUTOVISOR_TEST_BROWSER_CHANNEL=chrome.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

from playwright.async_api import async_playwright

from modules.course_runner import CourseOutcome, run_course
from modules.lesson_navigation import (
    FUSION_CATALOG,
    LEGACY_CATALOG,
    WISDOM_CATALOG,
    click_lesson,
    get_lesson_title,
    lesson_progress,
    wait_for_lesson_active,
)
from modules.utils import get_filtered_class
from modules.daily_study import DailyStudyBudget, SNAPSHOT_JS, StudyStore


class FusionCatalogTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        playwright = await async_playwright().start()
        self.addAsyncCleanup(playwright.stop)
        options = {"headless": True}
        channel = os.environ.get("AUTOVISOR_TEST_BROWSER_CHANNEL")
        if channel:
            options["channel"] = channel
        self.browser = await playwright.chromium.launch(**options)
        self.addAsyncCleanup(self.browser.close)
        self.page = await self.browser.new_page()
        self.page.set_default_timeout(2000)
        fixture = Path(__file__).parent / "fixtures" / "fusion_catalog.html"
        await self.page.set_content(fixture.read_text(encoding="utf-8"))

    async def row_ids(self, rows):
        return [await row.get_attribute("id") for row in rows]

    async def test_daily_snapshot_detects_visible_overlay_and_hidden_ancestor(self):
        await self.page.set_content('''
            <video></video>
            <div id="overlay"><div class="topic-title">Question</div></div>
        ''')
        state = await self.page.evaluate(SNAPSHOT_JS)
        self.assertTrue(state['blocked'])
        await self.page.locator('#overlay').evaluate("el => el.style.display = 'none'")
        state = await self.page.evaluate(SNAPSHOT_JS)
        self.assertFalse(state['blocked'])

    async def test_daily_budget_stops_browser_playback_and_survives_reopen(self):
        # Synthetic media clock: no course request, credentials or study upload.
        await self.page.set_content('''
            <div class="child-info hasvideo" onclick="this.classList.add('current')">
              <span class="child-name">Pending lesson</span>
              <span role="progressbar" aria-valuenow="0"></span>
            </div>
            <video></video>
            <script>
              window.pauseCalls = 0;
              const v = document.querySelector('video'), started = performance.now();
              Object.defineProperties(v, {
                currentTime: {get: () => (performance.now() - started) / 1000},
                duration: {get: () => 100},
                readyState: {get: () => 4},
                paused: {get: () => window.pauseCalls > 0},
                ended: {get: () => false},
                seeking: {get: () => false}
              });
              v.pause = () => {window.pauseCalls++};
            </script>
        ''')
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'history.sqlite3'
            store = StudyStore(path)
            try:
                budget = DailyStudyBudget(store, 'fixture-account', 'fixture-course', 30)
                store.consume(budget.account, budget.course, budget.day, 1799, 1800)
                gate = asyncio.Event()
                result = await asyncio.wait_for(run_course(
                    self.page, WISDOM_CATALOG, SimpleNamespace(limitMaxTime=0),
                    Mock(), gate, study_budget=budget,
                ), timeout=15)
                self.assertIs(result, CourseOutcome.DAILY_LIMIT)
                self.assertFalse(gate.is_set())
                self.assertGreater(await self.page.evaluate('window.pauseCalls'), 0)
                self.assertEqual(await lesson_progress(self.page.locator(WISDOM_CATALOG.item), WISDOM_CATALOG), 0)
            finally:
                store.close()
            reopened = StudyStore(path)
            try:
                self.assertTrue(DailyStudyBudget(reopened, 'fixture-account', 'fixture-course', 30).exhausted)
            finally:
                reopened.close()

    async def test_review_lists_nested_and_standalone_lessons_in_dom_order(self):
        rows = await get_filtered_class(self.page, FUSION_CATALOG, include_all=True)
        self.assertEqual(
            await self.row_ids(rows),
            ["lesson-531", "lesson-532", "lesson-533", "lesson-54"],
        )

    async def test_finished_sibling_does_not_hide_unfinished_children(self):
        rows = await get_filtered_class(self.page, FUSION_CATALOG)
        self.assertEqual(
            await self.row_ids(rows), ["lesson-532", "lesson-533", "lesson-54"]
        )
        self.assertEqual(
            [await lesson_progress(row, FUSION_CATALOG) for row in rows], [24, 0, 0]
        )
        self.assertEqual(
            await get_lesson_title(self.page, rows[0], FUSION_CATALOG),
            "5.3.2 Second lesson",
        )

    async def test_completion_moves_to_next_child_before_next_section(self):
        await self.page.locator("#lesson-532").evaluate(
            "el => el.insertAdjacentHTML('beforeend', '<span class=finish-icon></span>')"
        )
        rows = await get_filtered_class(self.page, FUSION_CATALOG)
        self.assertEqual(await self.row_ids(rows), ["lesson-533", "lesson-54"])

    async def test_fully_unfinished_group_keeps_first_child_and_individual_progress(self):
        await self.page.locator("#lesson-531 .finish-icon").evaluate("el => el.remove()")
        rows = await get_filtered_class(self.page, FUSION_CATALOG)
        self.assertEqual(
            await self.row_ids(rows),
            ["lesson-531", "lesson-532", "lesson-533", "lesson-54"],
        )
        self.assertEqual(
            [await lesson_progress(row, FUSION_CATALOG) for row in rows],
            [0, 24, 0, 0],
        )

    async def test_click_and_active_detection_target_the_exact_child(self):
        rows = await get_filtered_class(self.page, FUSION_CATALOG)
        await rows[0].click()
        self.assertTrue(await wait_for_lesson_active(rows[0], FUSION_CATALOG, 500))
        self.assertEqual(await self.page.evaluate("window.clickedLessons"), ["lesson-532"])
        self.assertEqual(
            await get_lesson_title(self.page, rows[0], FUSION_CATALOG),
            "5.3.2 Second lesson",
        )

    async def test_missing_label_does_not_use_a_title_elsewhere_on_page(self):
        await self.page.locator("#lesson-532 .item-name").evaluate(
            "el => el.replaceWith(document.createTextNode('Second lesson'))"
        )
        self.assertEqual(
            await get_lesson_title(self.page, self.page.locator("#lesson-532"), FUSION_CATALOG),
            "5.3.2 Second lesson",
        )

    async def test_deeply_nested_group_never_inherits_finished_sibling(self):
        await self.page.set_content('''
            <div class="chapter-item" id="outer">
              <span class="item-name">Heading</span>
              <div class="chapter-item" id="inner">
                <span class="item-name">Subheading</span>
                <section>
                  <div class="chapter-content-second" id="finished">
                    <span class="item-name">Finished</span><span class="finish-icon"></span>
                  </div>
                  <div class="chapter-content-second" id="pending">
                    <span class="item-name">Pending</span>
                    <span class="el-progress" aria-valuenow="35"></span>
                  </div>
                </section>
              </div>
            </div>
        ''')
        rows = await get_filtered_class(self.page, FUSION_CATALOG)
        self.assertEqual(await self.row_ids(rows), ["pending"])
        self.assertEqual(await lesson_progress(rows[0], FUSION_CATALOG), 35)

    async def test_click_uses_label_with_handler_instead_of_container_center(self):
        await self.page.set_content('''
            <div class="chapter-item" id="row" style="width:600px;height:100px">
              <div class="item-box">
                <span class="item-name" onclick="this.parentElement.classList.add('current')">
                  Select this label
                </span>
              </div>
            </div>
        ''')
        row = self.page.locator("#row")
        await row.click()
        self.assertFalse(await wait_for_lesson_active(row, FUSION_CATALOG, 1))
        await click_lesson(row, FUSION_CATALOG, 1000)
        self.assertTrue(await wait_for_lesson_active(row, FUSION_CATALOG, 200))

    async def test_active_sibling_does_not_activate_requested_lesson(self):
        await self.page.locator("#lesson-531").evaluate("el => el.classList.add('current')")
        self.assertFalse(await wait_for_lesson_active(
            self.page.locator("#lesson-532"), FUSION_CATALOG, 1
        ))

    async def test_legacy_click_uses_its_scoped_title(self):
        await self.page.set_content('''
            <li class="clearfix video" style="width:600px;height:100px">
              <span id="lessonOrder" onclick="this.parentElement.classList.add('current_play')">
                Legacy lesson
              </span>
            </li>
        ''')
        row = self.page.locator(LEGACY_CATALOG.item)
        await click_lesson(row, LEGACY_CATALOG, 1000)
        self.assertTrue(await wait_for_lesson_active(row, LEGACY_CATALOG, 200))

    async def test_existing_number_in_title_is_not_duplicated(self):
        row = self.page.locator("#lesson-531")
        await row.locator(".item-name").evaluate(
            "el => el.setAttribute('title', '5.3.1 First lesson')"
        )
        self.assertEqual(await get_lesson_title(self.page, row, FUSION_CATALOG), "5.3.1 First lesson")

    async def test_non_fusion_catalog_keeps_its_rows_and_titles(self):
        await self.page.set_content('''
            <div class="child-info hasvideo" id="done">
              <span class="child-check"></span><span class="child-name">Done</span>
            </div>
            <div class="child-info hasvideo" id="pending">
              <span class="child-name">Pending</span>
            </div>
        ''')
        rows = await get_filtered_class(self.page, WISDOM_CATALOG)
        self.assertEqual(await self.row_ids(rows), ["pending"])
        self.assertEqual(await get_lesson_title(self.page, rows[0], WISDOM_CATALOG), "Pending")

    async def test_course_runner_visits_remaining_children_before_standalone(self):
        learned = []

        async def complete_lesson(page, start, paused, lesson, catalog, config, logger):
            learned.append(await lesson.get_attribute("id"))
            await lesson.evaluate(
                "el => el.insertAdjacentHTML('beforeend', '<span class=finish-icon></span>')"
            )
            return 0.0, True, False

        with (
            patch("modules.course_runner.learn_lesson", side_effect=complete_lesson),
            patch("modules.course_runner.FusionAdapter.expand_catalog", new_callable=AsyncMock),
        ):
            result = await run_course(
                self.page, FUSION_CATALOG, SimpleNamespace(limitMaxTime=0),
                Mock(), asyncio.Event(),
            )
        self.assertEqual(result, CourseOutcome.COMPLETED)
        self.assertEqual(learned, ["lesson-532", "lesson-533", "lesson-54"])
        self.assertEqual(await self.page.evaluate("window.clickedLessons"), learned)

    async def test_all_completed_course_reviews_every_child_in_order(self):
        await self.page.locator('[id^="lesson-"]').evaluate_all(
            "rows => rows.forEach(el => el.insertAdjacentHTML("
            "'beforeend', '<span class=finish-icon></span>'))"
        )
        self.assertEqual(await get_filtered_class(self.page, FUSION_CATALOG), [])
        with (
            patch("modules.course_runner.learn_lesson", new_callable=AsyncMock) as learn,
            patch("modules.course_runner.review_lesson", new_callable=AsyncMock,
                  return_value=(0.0, True, False)) as review,
            patch("modules.course_runner.FusionAdapter.expand_catalog", new_callable=AsyncMock),
        ):
            result = await run_course(
                self.page, FUSION_CATALOG, SimpleNamespace(limitMaxTime=0, reviewCompletedCourses=True),
                Mock(), asyncio.Event(),
            )
        self.assertEqual(result, CourseOutcome.COMPLETED)
        learn.assert_not_awaited()
        self.assertEqual(review.await_count, 4)
        self.assertEqual(
            await self.page.evaluate("window.clickedLessons"),
            ["lesson-531", "lesson-532", "lesson-533", "lesson-54"],
        )


if __name__ == "__main__":
    unittest.main()
