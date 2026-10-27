"""純粋関数と PDF 結合のテスト（macOS 操作は対象外）。実行: .venv/bin/python -m unittest -v"""

import argparse
import re
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

import image_ops
import kindle2pdf


def page_with_box(box, size=(200, 300), bg="white"):
    img = Image.new("RGB", size, bg)
    ImageDraw.Draw(img).rectangle(box, fill="black")
    return img


class IsSamePageTest(unittest.TestCase):
    def test_identical_images_are_same(self):
        a = page_with_box((50, 50, 150, 250))
        self.assertTrue(image_ops.is_same_page(a, a.copy()))

    def test_different_content_is_not_same(self):
        a = page_with_box((50, 50, 150, 250))
        b = page_with_box((20, 20, 100, 100))
        self.assertFalse(image_ops.is_same_page(a, b))

    def test_tiny_change_is_ignored(self):
        a = page_with_box((50, 50, 150, 250), size=(1000, 1000))
        b = a.copy()
        b.putpixel((0, 0), (0, 0, 0))
        self.assertTrue(image_ops.is_same_page(a, b))

    def test_different_size_is_not_same(self):
        self.assertFalse(image_ops.is_same_page(Image.new("RGB", (10, 10)), Image.new("RGB", (10, 11))))


class BBoxTest(unittest.TestCase):
    def test_content_bbox_finds_content_area(self):
        self.assertEqual(image_ops.content_bbox(page_with_box((50, 60, 150, 250))), (50, 60, 151, 251))

    def test_content_bbox_blank_page_is_none(self):
        self.assertIsNone(image_ops.content_bbox(Image.new("RGB", (50, 50), "white")))

    def test_union_ignores_none(self):
        self.assertEqual(image_ops.union_bbox([(10, 10, 20, 20), None, (5, 15, 30, 18)]), (5, 10, 30, 20))
        self.assertIsNone(image_ops.union_bbox([None]))

    def test_pad_is_clamped_to_image(self):
        self.assertEqual(image_ops.pad_bbox((2, 2, 98, 98), 10, (100, 100)), (0, 0, 100, 100))


class BuildPdfTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.paths = []
        for i, box in enumerate([(50, 50, 150, 250), (40, 70, 120, 200)], start=1):
            path = self.dir / f"page_{i:04d}.png"
            page_with_box(box).save(path)
            self.paths.append(path)

    def test_builds_pdf_with_all_pages(self):
        output = self.dir / "book.pdf"
        crop = image_ops.common_crop_box(self.paths, padding=0)
        self.assertEqual(crop, (40, 50, 151, 251))
        self.assertEqual(image_ops.build_pdf(self.paths, output, crop=crop), 2)
        self.assertEqual(len(re.findall(rb"/Type\s*/Page\b", output.read_bytes())), 2)

    def test_refuses_to_overwrite(self):
        output = self.dir / "book.pdf"
        output.write_bytes(b"existing")
        with self.assertRaises(FileExistsError):
            image_ops.build_pdf(self.paths, output)
        self.assertEqual(output.read_bytes(), b"existing")

    def test_empty_input_raises(self):
        with self.assertRaises(ValueError):
            image_ops.build_pdf([], self.dir / "x.pdf")

    def test_build_book_names_pdf_after_folder(self):
        output = kindle2pdf.build_book(self.dir, trim=True)
        self.assertEqual(output, self.dir / f"{self.dir.name}.pdf")
        self.assertTrue(output.exists())


class CliHelpersTest(unittest.TestCase):
    def test_parse_region(self):
        self.assertEqual(kindle2pdf.parse_region("0,25,1440,875"), (0, 25, 1440, 875))
        self.assertIsNone(kindle2pdf.parse_region(None))

    def test_parse_region_rejects_bad_input(self):
        for bad in ["1,2,3", "a,b,c,d", "0,0,0,100"]:
            with self.assertRaises(argparse.ArgumentTypeError):
                kindle2pdf.parse_region(bad)

    def test_safe_title_replaces_path_chars(self):
        self.assertEqual(kindle2pdf.safe_title(" 上/下:巻 "), "上_下_巻")
        with self.assertRaises(ValueError):
            kindle2pdf.safe_title("   ")

    def test_page_path_is_zero_padded(self):
        self.assertEqual(kindle2pdf.page_path(Path("d"), 7).name, "page_0007.png")


if __name__ == "__main__":
    unittest.main()
