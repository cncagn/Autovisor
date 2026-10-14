from pathlib import Path
import tempfile
import unittest
from modules.configs import Config, ConfigError

ROOT = Path(__file__).resolve().parents[1]


class DailyConfigTests(unittest.TestCase):
    def config(self, extra):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'config.ini'
        text = (ROOT / 'config.ini.example').read_text(encoding='utf-8-sig')
        text = '\n'.join(line for line in text.splitlines()
                         if not line.startswith(('dailyLimitMinutes', 'studyProfile', 'reviewCompletedCourses')))
        text = text.replace('[course-option]', '[course-option]\n' + extra)
        path.write_text(text, encoding='utf-8')
        return Config(path, ROOT / 'data/mirrors.json')

    def test_old_config_keeps_session_timer_and_has_no_daily_limit(self):
        config = self.config('')
        self.assertEqual(config.dailyLimitMinutes, 0)
        self.assertFalse(config.reviewCompletedCourses)

    def test_daily_settings_are_read(self):
        config = self.config('dailyLimitMinutes=30\nstudyProfile=account2\nreviewCompletedCourses=True')
        self.assertEqual(config.dailyLimitMinutes, 30)
        self.assertEqual(config.studyProfile, 'account2')
        self.assertTrue(config.reviewCompletedCourses)

    def test_invalid_daily_limit_fails_instead_of_becoming_unlimited(self):
        for value in ('nan', 'inf', '-1', 'thirty', ''):
            with self.subTest(value=value), self.assertRaises(ConfigError):
                self.config('dailyLimitMinutes=' + value).dailyLimitMinutes
