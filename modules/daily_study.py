"""Durable local playback time; this does not represent server-awarded credit."""
import asyncio
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, unquote, urlencode, urlsplit, urlunsplit

SHANGHAI = timezone(timedelta(hours=8))
SAMPLE_INTERVAL = 0.5
MAX_SAMPLE_GAP = 2.0


def china_now():
    return datetime.now(SHANGHAI)


def course_key(url: str) -> str:
    parts = urlsplit(url.strip())
    query = parse_qs(parts.query)
    for name in ("recruitAndCourseId", "courseId"):
        if query.get(name):
            return f"zhihuishu:{name}:{query[name][0]}"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path,
                      urlencode(sorted(query.items()), doseq=True), ""))


def account_key(cookies, profile: str = "") -> str:
    """Use an explicit profile or authenticated ID, never changing session tokens."""
    if profile.strip():
        return hashlib.sha256(("profile:" + profile.strip()).encode("utf-8")).hexdigest()
    identity = None
    for cookie in cookies or []:
        domain = (cookie.get("domain") or "").lstrip(".").lower()
        if domain != "zhihuishu.com" and not domain.endswith(".zhihuishu.com"):
            continue
        name = cookie.get("name", "").lower()
        value = unquote(str(cookie.get("value", "")))
        if name == "caslogc":
            try:
                data = json.loads(value)
            except (ValueError, TypeError):
                continue
            if isinstance(data, dict):
                for field in ("userId", "userid", "uid"):
                    candidate = data.get(field)
                    if isinstance(candidate, (str, int)) and not isinstance(candidate, bool) and str(candidate).strip():
                        identity = "user:" + str(candidate).strip()
                        break
        if identity:
            break
    if not identity:
        raise ValueError("无法读取登录账号标识，请在 [course-option] 配置 studyProfile（每个账号使用不同名字）。")
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


class StudyStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=5)
        try:
            self.connection.execute("""CREATE TABLE IF NOT EXISTS daily_study (
                account TEXT NOT NULL, course TEXT NOT NULL, day TEXT NOT NULL,
                seconds REAL NOT NULL CHECK(seconds >= 0),
                PRIMARY KEY (account, course, day))""")
            self.connection.commit()
        except BaseException:
            self.connection.close()
            raise

    def close(self):
        self.connection.close()

    def seconds(self, account, course, day):
        row = self.connection.execute(
            "SELECT seconds FROM daily_study WHERE account=? AND course=? AND day=?",
            (account, course, day),
        ).fetchone()
        return row[0] if row else 0.0

    def total(self, account, course):
        return self.connection.execute(
            "SELECT COALESCE(SUM(seconds), 0) FROM daily_study WHERE account=? AND course=?",
            (account, course),
        ).fetchone()[0]

    def consume(self, account, course, day, seconds, limit_seconds):
        if not math.isfinite(seconds) or seconds < 0:
            raise ValueError("学习时长必须为非负有限值")
        if not math.isfinite(limit_seconds) or limit_seconds <= 0:
            raise ValueError("每日限额必须为正有限值")
        try:
            # Read and add under one transaction: competing processes cannot
            # lose increments or each spend the same remaining quota.
            self.connection.execute("BEGIN IMMEDIATE")
            previous = self.seconds(account, course, day)
            added = min(seconds, max(0.0, limit_seconds - previous))
            self.connection.execute(
                """INSERT INTO daily_study(account, course, day, seconds) VALUES (?, ?, ?, ?)
                ON CONFLICT(account, course, day) DO UPDATE SET seconds=excluded.seconds""",
                (account, course, day, previous + added),
            )
            self.connection.commit()
            return added
        except BaseException:
            self.connection.rollback()
            raise

    def history(self):
        return self.connection.execute(
            "SELECT account, course, day, seconds FROM daily_study ORDER BY day DESC, account, course"
        ).fetchall()


SNAPSHOT_JS = """() => {
    const video = document.querySelector('video');
    if (!video) return null;
    const blocked = [...document.querySelectorAll(
        '.yidun_popup .yidun_modal, .yidun_modal__title, [id^="tcaptcha_transform"], ' +
        '.topic-title, .ss2077-custom-dialog, .ai-class-exercise-dialog'
    )].some(el => {
        const style = getComputedStyle(el);
        return el.getClientRects().length > 0 && style.display !== 'none' &&
            style.visibility !== 'hidden' && Number(style.opacity || 1) > 0.05;
    });
    return {currentTime: video.currentTime, playbackRate: video.playbackRate,
        paused: video.paused, ended: video.ended, seeking: video.seeking,
        readyState: video.readyState, source: video.currentSrc || video.src,
        blocked};
}"""


def _valid_snapshot(snapshot):
    if not isinstance(snapshot, dict):
        return False
    current = snapshot.get("currentTime")
    rate = snapshot.get("playbackRate")
    return (
        isinstance(current, (int, float)) and math.isfinite(current) and current >= 0
        and isinstance(rate, (int, float)) and math.isfinite(rate) and rate > 0
        and snapshot.get("readyState", 0) >= 3
        and not snapshot.get("seeking") and not snapshot.get("blocked")
    )


class DailyStudyBudget:
    def __init__(self, store, account, course, limit_minutes, now=china_now):
        self.store, self.account, self.course = store, account, course
        self.limit_seconds = float(limit_minutes) * 60
        if not math.isfinite(self.limit_seconds) or self.limit_seconds <= 0:
            raise ValueError("每日限额必须为正有限值")
        self.now = now
        self.previous = None
        self.stopped = False

    @property
    def day(self):
        return self.now().astimezone(SHANGHAI).date().isoformat()

    @property
    def today_seconds(self):
        return self.store.seconds(self.account, self.course, self.day)

    @property
    def exhausted(self):
        return self.stopped or self.today_seconds >= self.limit_seconds

    def report(self, logger):
        used = self.today_seconds
        remaining = max(0, self.limit_seconds - used)
        logger.info(f"今日已学 {used / 60:.2f} 分钟，剩余 {remaining / 60:.2f} 分钟；"
                    f"历史累计 {self.store.total(self.account, self.course) / 60:.2f} 分钟。")
        logger.event("每日学习记录", 日期=self.day, 账号标识=self.account[:8],
                     今日秒=round(used, 2), 剩余秒=round(remaining, 2))

    def observe(self, snapshot, enabled, mono=None, wall=None):
        mono = time.monotonic() if mono is None else mono
        wall = self.now() if wall is None else wall
        wall = wall.astimezone(SHANGHAI)
        previous = self.previous
        self.previous = (snapshot, enabled, mono, wall)
        if previous is None:
            return 0.0
        old, was_enabled, old_mono, old_wall = previous
        if not (enabled and was_enabled and _valid_snapshot(old) and _valid_snapshot(snapshot)):
            return 0.0
        if old.get("paused") or old.get("ended") or (snapshot.get("paused") and not snapshot.get("ended")):
            return 0.0
        elapsed = mono - old_mono
        wall_elapsed = (wall - old_wall).total_seconds()
        if not 0 < elapsed <= MAX_SAMPLE_GAP or wall_elapsed <= 0 or abs(wall_elapsed - elapsed) > 0.5:
            return 0.0
        if old.get("source") != snapshot.get("source") or old["playbackRate"] != snapshot["playbackRate"]:
            return 0.0
        advance = snapshot["currentTime"] - old["currentTime"]
        expected = elapsed * old["playbackRate"]
        if advance <= 0 or advance > expected + 0.35:
            return 0.0  # Frozen playback, rewind, or seek: never charge a jump.
        seconds = min(elapsed, advance / old["playbackRate"])
        start = wall - timedelta(seconds=seconds)
        charged = 0.0
        while start < wall:
            midnight = datetime.combine(start.date() + timedelta(days=1), datetime.min.time(), SHANGHAI)
            end = min(midnight, wall)
            day = start.date().isoformat()
            requested = (end - start).total_seconds()
            charged += self.store.consume(self.account, self.course, day, requested, self.limit_seconds)
            if self.store.seconds(self.account, self.course, day) >= self.limit_seconds:
                self.stopped = True
                break
            start = end
        return charged

    async def monitor(self, page, playback_enabled, logger):
        from playwright._impl._errors import TargetClosedError

        previous_day = self.day
        next_report = time.monotonic() + 60
        while True:
            if self.exhausted:
                return "daily_limit"
            try:
                snapshot = await page.evaluate(SNAPSHOT_JS)
                self.observe(snapshot, playback_enabled.is_set())
            except TargetClosedError:
                return "closed"
            except Exception as exc:
                if "Execution context was destroyed" not in str(exc):
                    raise
                self.previous = None
                logger.debug_throttled("daily_study", "每日计时等待页面切换完成。")
            if self.day != previous_day or time.monotonic() >= next_report:
                previous_day = self.day
                next_report = time.monotonic() + 60
                self.report(logger)
            if self.exhausted:
                return "daily_limit"
            await asyncio.sleep(SAMPLE_INTERVAL)
