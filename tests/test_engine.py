import os
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.engine.semantic_engine import (
    compute_semantic_access_entropy,
    compute_access_entropy,
    predict_future_relevance,
)


class TestSAEFormula(unittest.TestCase):
    """Test Semantic Access Entropy urgency scoring with mock files."""

    def setUp(self):
        self.now = time.time()
        self.mock_files = [
            {
                "path": "/data/active_module.py",
                "size_bytes": 4096,
                "last_modified": self.now - 7 * 86400,
                "desc": "recent Python source",
            },
            {
                "path": "/var/log/stale_app.log",
                "size_bytes": 524288,
                "last_modified": self.now - 200 * 86400,
                "desc": "stale log file",
            },
            {
                "path": "/tmp/ancient_backup.bak",
                "size_bytes": 1024,
                "last_modified": self.now - 400 * 86400,
                "desc": "ancient backup",
            },
        ]

    @patch("src.engine.semantic_engine.update_semantic_data")
    @patch("src.engine.semantic_engine.analyze_with_llm", return_value=None)
    @patch("src.engine.semantic_engine.read_file_sample", return_value=None)
    @patch("src.engine.semantic_engine.get_access_history", return_value=[])
    def test_urgency_scores_within_bounds(self, _history, _read, _llm, _update):
        for fmeta in self.mock_files:
            with self.subTest(file=fmeta["desc"]):
                result = compute_semantic_access_entropy(
                    path=fmeta["path"],
                    size_bytes=fmeta["size_bytes"],
                    last_modified=fmeta["last_modified"],
                )
                urgency = result["archival_urgency"]
                self.assertGreaterEqual(urgency, 0.0, msg=fmeta["desc"])
                self.assertLessEqual(urgency, 1.0, msg=fmeta["desc"])

    @patch("src.engine.semantic_engine.get_access_history", return_value=[])
    def test_future_relevance_bounds(self, _history):
        for fmeta in self.mock_files:
            with self.subTest(file=fmeta["desc"]):
                score = predict_future_relevance(
                    fmeta["path"],
                    fmeta["size_bytes"],
                    fmeta["last_modified"],
                    access_entropy=0.5,
                )
                self.assertGreaterEqual(score, 0.0)
                self.assertLessEqual(score, 1.0)

    def test_access_entropy_default_no_events(self):
        with patch("src.engine.semantic_engine.get_access_history", return_value=[]):
            entropy = compute_access_entropy("/some/file.txt")
            self.assertGreaterEqual(entropy, 0.0)
            self.assertLessEqual(entropy, 1.0)

    @patch("src.engine.semantic_engine.update_semantic_data")
    @patch("src.engine.semantic_engine.analyze_with_llm", return_value=None)
    @patch("src.engine.semantic_engine.read_file_sample", return_value=None)
    @patch("src.engine.semantic_engine.get_access_history", return_value=[])
    def test_older_files_have_higher_urgency(self, _history, _read, _llm, _update):
        results = []
        for fmeta in self.mock_files:
            result = compute_semantic_access_entropy(
                path=fmeta["path"],
                size_bytes=fmeta["size_bytes"],
                last_modified=fmeta["last_modified"],
            )
            results.append(result)

        active_urgency = results[0]["archival_urgency"]
        ancient_urgency = results[2]["archival_urgency"]
        self.assertGreater(ancient_urgency, active_urgency)


if __name__ == "__main__":
    unittest.main()
