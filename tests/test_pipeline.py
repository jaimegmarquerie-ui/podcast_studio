"""Small automatic tests. Run from the project folder with:

    python -m unittest discover tests

They need no internet and no API key: the external services are replaced by
fake functions (mocks).
"""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import data_processor  # noqa: E402
import llm_processor  # noqa: E402
import tts_generator  # noqa: E402

SHEET = (
    "Título: El jardinero y la muerte\n"
    "Autor: Georgi Gospodinov\n"
    "Género: Novela\n"
    "Un hijo acompaña a su padre en sus últimos días y recuerda el jardín."
)


class DataProcessorTests(unittest.TestCase):
    def test_extracts_metadata_in_spanish_or_english(self):
        sheet = data_processor.parse_sheet(SHEET)
        self.assertEqual(sheet["metadata"]["title"], "El jardinero y la muerte")
        self.assertEqual(sheet["metadata"]["author"], "Georgi Gospodinov")
        self.assertEqual(sheet["metadata"]["genre"], "Novela")

    def test_title_falls_back_to_first_line(self):
        sheet = data_processor.parse_sheet("# My episode\n" + "word " * 20)
        self.assertEqual(sheet["metadata"]["title"], "My episode")

    def test_rejects_short_text(self):
        with self.assertRaises(ValueError):
            data_processor.parse_sheet("too short")

    def test_clean_text_removes_extra_spaces_and_blank_lines(self):
        self.assertEqual(data_processor.clean_text("a   b\n\n\n\nc"), "a b\n\nc")

    def test_reads_txt_and_rejects_unknown_types(self):
        folder = Path(tempfile.mkdtemp())
        good = folder / "book.txt"
        good.write_text(SHEET, encoding="utf-8")
        self.assertIn("Gospodinov", data_processor.read_text_file(good))
        bad = folder / "book.docx"
        bad.write_text("x")
        with self.assertRaises(ValueError):
            data_processor.read_text_file(bad)


class PromptTests(unittest.TestCase):
    def test_prompt_contains_sheet_and_style(self):
        sheet = data_processor.parse_sheet(SHEET)
        prompt = llm_processor.build_prompt(sheet, "Quick summary (about 2 min)")
        self.assertIn("Gospodinov", prompt)
        self.assertIn("2 minutes", prompt)


class AudioFallbackTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())

    @staticmethod
    def _fail(*args):
        raise RuntimeError("service down")

    def test_uses_chosen_voice_when_gemini_works(self):
        ok = lambda text, voice, path: path.write_bytes(b"audio")  # noqa: E731
        with mock.patch.object(tts_generator, "_gemini_tts_save", ok):
            path, used = tts_generator.generate_audio("hi", self.folder, "Charon - informative")
        self.assertEqual(used, "Charon - informative")
        self.assertTrue(path.exists())

    def test_falls_back_to_edge_then_gtts(self):
        ok = lambda text, path: path.write_bytes(b"audio")  # noqa: E731
        with mock.patch.object(tts_generator, "_gemini_tts_save", self._fail), \
                mock.patch.object(tts_generator, "_edge_tts_save", ok):
            _, used = tts_generator.generate_audio("hi", self.folder)
        self.assertEqual(used, tts_generator.EDGE_NAME)
        with mock.patch.object(tts_generator, "_gemini_tts_save", self._fail), \
                mock.patch.object(tts_generator, "_edge_tts_save", self._fail), \
                mock.patch.object(tts_generator, "_gtts_save", ok):
            _, used = tts_generator.generate_audio("hi", self.folder)
        self.assertEqual(used, tts_generator.GTTS_NAME)

    def test_raises_when_all_providers_fail(self):
        with mock.patch.object(tts_generator, "_gemini_tts_save", self._fail), \
                mock.patch.object(tts_generator, "_edge_tts_save", self._fail), \
                mock.patch.object(tts_generator, "_gtts_save", self._fail):
            with self.assertRaises(RuntimeError):
                tts_generator.generate_audio("hi", self.folder)


if __name__ == "__main__":
    unittest.main()
