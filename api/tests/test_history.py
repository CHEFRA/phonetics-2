import unittest

from src.services import history


class HistoryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = history.start_session(app="test", model="SenseVoiceSmall")
        for i in range(5):
            history.record_transcription(
                session_id=cls.session,
                source="desktop",
                model="SenseVoiceSmall"
                if i % 2 == 0
                else "paraformer-zh-streaming",
                text=f"测试文本{i}",
                status="success",
                audio_duration_ms=1000 + i,
                inference_ms=200 + i,
                rtf=0.2 + i / 1000,
                mode="batch" if i % 2 == 0 else "stream",
            )

    def test_recent_ordering(self):
        rows = history.recent(3)
        self.assertEqual(len(rows), 3)
        self.assertGreater(rows[0]["id"], rows[1]["id"])

    def test_pagination_and_search(self):
        rows, total = history.list_transcriptions(limit=2, offset=0, query="文本")
        self.assertEqual(len(rows), 2)
        self.assertEqual(total, 5)
        rows2, total2 = history.list_transcriptions(
            limit=2, offset=2, query="文本"
        )
        self.assertEqual(total2, 5)
        self.assertNotEqual(rows[0]["id"], rows2[0]["id"])

    def test_status_filter(self):
        _, total = history.list_transcriptions(status="empty")
        self.assertEqual(total, 0)

    def test_models_share(self):
        share = history.models_share()
        self.assertEqual(sum(item["cnt"] for item in share), 5)
        self.assertAlmostEqual(sum(item["pct"] for item in share), 100.0)

    def test_latency_trend(self):
        trend = history.latency_trend(30)
        self.assertTrue(trend)
        self.assertIn("avg_inference_ms", trend[-1])
        self.assertIn("avg_rtf", trend[-1])
