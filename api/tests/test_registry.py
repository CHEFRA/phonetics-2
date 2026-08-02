import unittest

from src.core import asr_registry


class RegistryTest(unittest.TestCase):
    def tearDown(self):
        asr_registry.set_active_model("sensevoice")

    def test_available_models(self):
        self.assertEqual(
            sorted(asr_registry.available_models()),
            ["paraformer-streaming", "sensevoice"],
        )

    def test_same_instance(self):
        self.assertIs(
            asr_registry.get_asr_service(),
            asr_registry.get_asr_service(),
        )

    def test_switch_resets_service(self):
        svc1 = asr_registry.get_asr_service()
        self.assertEqual(svc1.name, "sensevoice")
        asr_registry.set_active_model("paraformer-streaming")
        svc2 = asr_registry.get_asr_service()
        self.assertEqual(svc2.name, "paraformer-streaming")
        self.assertIsNot(svc1, svc2)

    def test_invalid_model(self):
        with self.assertRaises(ValueError):
            asr_registry.set_active_model("unknown")

    def test_model_dir_update(self):
        asr_registry.set_model_dir("sensevoice", "C:/fake/model")
        self.assertEqual(
            asr_registry.get_model_dir("sensevoice"), "C:/fake/model"
        )
        asr_registry.set_model_dir("sensevoice", "SenseVoiceSmall")
