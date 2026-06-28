# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


TEST_OUTPUTS_PATH = Path(__file__).with_name("test_outputs.py")


def _build_stub_modules():
    docx_module = types.ModuleType("docx")

    class UnpatchedDocument:
        def __init__(self, *args, **kwargs):
            raise AssertionError("Document should be patched in tests")

    docx_module.Document = UnpatchedDocument

    docx_enum_module = types.ModuleType("docx.enum")
    docx_enum_text_module = types.ModuleType("docx.enum.text")
    docx_enum_text_module.WD_PARAGRAPH_ALIGNMENT = types.SimpleNamespace(CENTER="center")
    docx_enum_text_module.WD_TAB_ALIGNMENT = types.SimpleNamespace(
        CLEAR="clear",
        LEFT="left",
        RIGHT="right",
    )
    docx_enum_module.text = docx_enum_text_module

    docx_shared_module = types.ModuleType("docx.shared")

    class RGBColor:
        def __init__(self, *args):
            self.rgb = args

    docx_shared_module.RGBColor = RGBColor

    fitz_module = types.ModuleType("fitz")
    numpy_module = types.ModuleType("numpy")

    pil_module = types.ModuleType("PIL")
    pil_image_module = types.ModuleType("PIL.Image")
    pil_module.Image = pil_image_module

    odf_module = types.ModuleType("odf")
    odf_opendocument_module = types.ModuleType("odf.opendocument")
    odf_opendocument_module.load = lambda *args, **kwargs: None
    odf_text_module = types.ModuleType("odf.text")
    odf_text_module.P = type("P", (), {})
    odf_text_module.Span = type("Span", (), {})

    rapidfuzz_module = types.ModuleType("rapidfuzz")
    rapidfuzz_module.fuzz = types.SimpleNamespace(ratio=lambda *args, **kwargs: 0.0)

    skimage_module = types.ModuleType("skimage")
    skimage_color_module = types.ModuleType("skimage.color")
    skimage_color_module.deltaE_ciede2000 = lambda *args, **kwargs: 0.0
    skimage_color_module.rgb2lab = lambda *args, **kwargs: (0.0, 0.0, 0.0)

    return {
        "docx": docx_module,
        "docx.enum": docx_enum_module,
        "docx.enum.text": docx_enum_text_module,
        "docx.shared": docx_shared_module,
        "fitz": fitz_module,
        "numpy": numpy_module,
        "PIL": pil_module,
        "PIL.Image": pil_image_module,
        "odf": odf_module,
        "odf.opendocument": odf_opendocument_module,
        "odf.text": odf_text_module,
        "rapidfuzz": rapidfuzz_module,
        "skimage": skimage_module,
        "skimage.color": skimage_color_module,
    }


def _load_test_outputs_module():
    spec = importlib.util.spec_from_file_location(
        "writer_tabstops_first_three_words_test_outputs",
        TEST_OUTPUTS_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, _build_stub_modules()):
        assert spec.loader is not None
        spec.loader.exec_module(module)
    return module


class _FakeTabStop:
    def __init__(self, position, alignment):
        self.position = position
        self.alignment = alignment


class _FakeParagraph:
    def __init__(self, text, tab_stops=None):
        self.text = text
        self.paragraph_format = types.SimpleNamespace(tab_stops=tab_stops or [])


class _FakeSection:
    def __init__(self, paragraph_width):
        self.page_width = paragraph_width + 20
        self.left_margin = 10
        self.right_margin = 10


class _FakeDocument:
    def __init__(self, paragraphs, paragraph_width=100):
        self.paragraphs = paragraphs
        self.sections = [_FakeSection(paragraph_width)]


class CheckTabstopsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = _load_test_outputs_module()

    def _run_check(self, doc_map, **kwargs):
        with patch.object(self.module, "Document", side_effect=lambda path: doc_map[path]):
            return self.module.check_tabstops("pred", "gold", **kwargs)

    def test_exact_match_returns_full_score(self):
        right = self.module.WD_TAB_ALIGNMENT.RIGHT
        doc_map = {
            "pred": _FakeDocument(
                [_FakeParagraph("one two three\tfour", [_FakeTabStop(100, right)])]
            ),
            "gold": _FakeDocument(
                [_FakeParagraph("one two three\tfour", [_FakeTabStop(100, right)])]
            ),
        }

        score = self._run_check(doc_map, word_number_split_by_tabstop=3, index=0)

        self.assertEqual(1.0, score)

    def test_large_tab_mismatch_is_clamped_to_zero(self):
        right = self.module.WD_TAB_ALIGNMENT.RIGHT
        doc_map = {
            "pred": _FakeDocument(
                [_FakeParagraph("one two three\tfour", [_FakeTabStop(260, right)])],
                paragraph_width=100,
            ),
            "gold": _FakeDocument(
                [_FakeParagraph("one two three\tfour", [_FakeTabStop(100, right)])],
                paragraph_width=100,
            ),
        }

        score = self._run_check(doc_map, word_number_split_by_tabstop=3, index=0)

        self.assertEqual(0.0, score)

    def test_missing_requested_tab_returns_zero(self):
        right = self.module.WD_TAB_ALIGNMENT.RIGHT
        doc_map = {
            "pred": _FakeDocument(
                [_FakeParagraph("one two three four", [_FakeTabStop(100, right)])]
            ),
            "gold": _FakeDocument(
                [_FakeParagraph("one two three four", [_FakeTabStop(100, right)])]
            ),
        }

        score = self._run_check(doc_map, word_number_split_by_tabstop=3, index=1)

        self.assertEqual(0.0, score)

    def test_empty_documents_return_zero(self):
        doc_map = {
            "pred": _FakeDocument([_FakeParagraph(""), _FakeParagraph("   ")]),
            "gold": _FakeDocument([_FakeParagraph(""), _FakeParagraph("   ")]),
        }

        score = self._run_check(doc_map)

        self.assertEqual(0.0, score)


if __name__ == "__main__":
    unittest.main()
