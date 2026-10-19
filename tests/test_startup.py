import importlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


class StartupTests(unittest.TestCase):
    def test_importing_voice_support_does_not_download_ffmpeg(self):
        """Text-only startup and offline tests must not bootstrap an audio binary."""
        add_paths = Mock(side_effect=AssertionError("unexpected audio bootstrap"))
        with patch.dict(sys.modules, {"static_ffmpeg": SimpleNamespace(add_paths=add_paths)}):
            module = importlib.import_module("utils.speech_to_text")
            importlib.reload(module)
        add_paths.assert_not_called()

    def test_missing_voice_file_does_not_initialize_audio(self):
        import asyncio
        from utils import speech_to_text
        with patch.object(speech_to_text.os.path, "exists", return_value=False), patch.object(speech_to_text, "ensure_ffmpeg") as prepare:
            self.assertEqual(asyncio.run(speech_to_text.convert_voice_to_text("missing.oga")), "ERROR_FILE_NOT_FOUND")
        prepare.assert_not_called()
