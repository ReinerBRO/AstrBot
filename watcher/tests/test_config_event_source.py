import os
import unittest
from unittest.mock import patch

from watcher.config import load_config


class EventConfigTest(unittest.TestCase):
    def test_event_source_config_defaults(self):
        with patch("watcher.config._load_env", return_value=None), patch.dict(
            os.environ, {}, clear=True
        ):
            config = load_config()
            self.assertTrue(config.enable_event_source)
            self.assertFalse(config.event_privacy_mask)
            self.assertEqual(config.event_buffer_window_s, 300)
            self.assertEqual(config.event_log_dir, "logs")

    def test_event_source_config_env_override(self):
        with patch("watcher.config._load_env", return_value=None), patch.dict(
            os.environ,
            {
                "ENABLE_EVENT_SOURCE": "false",
                "EVENT_PRIVACY_MASK": "true",
                "EVENT_BUFFER_WINDOW_S": "600",
                "EVENT_LOG_DIR": "custom-logs",
                "WATCH_START": "09:00",
                "WATCH_END": "18:00",
            },
            clear=True,
        ):
            config = load_config()
            self.assertFalse(config.enable_event_source)
            self.assertTrue(config.event_privacy_mask)
            self.assertEqual(config.event_buffer_window_s, 600)
            self.assertEqual(config.event_log_dir, "custom-logs")


if __name__ == "__main__":
    unittest.main()
