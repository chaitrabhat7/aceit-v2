"""Plain-script tests for vision.transcribe_images — fake Vision client, no live API.

Run:  python test_vision.py
"""
import io
import sys

from PIL import Image

import vision


# ─── Fakes ───────────────────────────────────────────────────────────────
def fake_upload(size=(400, 300)):
    """A file-like object mimicking a Streamlit UploadedFile."""
    buf = io.BytesIO()
    Image.new("RGB", size, (255, 255, 255)).save(buf, format="PNG")
    buf.seek(0)
    return buf


class _Resp:
    def __init__(self, text="", error_message=""):
        self.full_text_annotation = type("A", (), {"text": text})()
        self.error = type("E", (), {"message": error_message})()


class FakeClient:
    """Returns canned per-image results; records how many images per batch call."""
    def __init__(self, results):
        self._results = list(results)      # list of (text, error_message)
        self.batch_sizes = []

    def batch_annotate_images(self, requests):
        self.batch_sizes.append(len(requests))
        picked = [self._results.pop(0) for _ in requests]
        return type("B", (), {"responses": [_Resp(t, e) for t, e in picked]})()


def use_fake(results):
    fake = FakeClient(results)
    vision._build_client = lambda *a, **k: fake
    return fake


# ─── Tests ───────────────────────────────────────────────────────────────
def test_normal_multi_image():
    use_fake([("PAGE ONE", ""), ("PAGE TWO", ""), ("PAGE THREE", "")])
    out = vision.transcribe_images([fake_upload(), fake_upload(), fake_upload()])
    assert out["pages"] == ["PAGE ONE", "PAGE TWO", "PAGE THREE"], out
    assert out["ocr_failed"] == [] and len(out["jpegs"]) == 3, out


def test_one_page_errors():
    use_fake([("PAGE ONE", ""), ("", "IMAGE_UNREADABLE"), ("PAGE THREE", "")])
    out = vision.transcribe_images([fake_upload() for _ in range(3)])
    assert out["pages"] == ["PAGE ONE", "", "PAGE THREE"], out
    assert out["ocr_failed"] == [2] and len(out["jpegs"]) == 3, out


def test_blank_page_counts_as_failed():
    use_fake([("", ""), ("REAL TEXT", "")])
    out = vision.transcribe_images([fake_upload() for _ in range(2)])
    assert out["pages"] == ["", "REAL TEXT"] and out["ocr_failed"] == [1], out


def test_single_image():
    use_fake([("SOLO PAGE", "")])
    out = vision.transcribe_images([fake_upload()])
    assert out["pages"] == ["SOLO PAGE"] and out["ocr_failed"] == [], out


def test_empty_list_raises():
    try:
        vision.transcribe_images([])
    except ValueError:
        return
    raise AssertionError("expected ValueError on empty list")


def test_batches_of_16():
    fake = use_fake([("x", "")] * 20)
    out = vision.transcribe_images([fake_upload() for _ in range(20)])
    assert len(out["pages"]) == 20 and len(out["jpegs"]) == 20, out
    assert fake.batch_sizes == [16, 4], fake.batch_sizes


def test_downscale_applied():
    big = io.BytesIO()
    Image.new("RGB", (5000, 4000), (200, 200, 200)).save(big, format="PNG")
    big.seek(0)
    jpeg = vision._downscale_to_jpeg(big.read())
    img = Image.open(io.BytesIO(jpeg))
    assert max(img.size) == vision._MAX_EDGE_PX, img.size
    assert img.format == "JPEG", img.format


# ─── Runner ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except Exception as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
