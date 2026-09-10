"""Chapter / page image -> text via Google Cloud Vision OCR.

One path for the tutor-mode uploader: 1..N page images. A spread photo is two
book pages; N=1 is a single quick-question page. Each image is downscaled,
then all are sent to Google Vision DOCUMENT_TEXT_DETECTION in batches of 16.

Returns the text per page plus the (1-based) positions that came back empty,
so app.py can join the pages in upload order and tell the student which photos
to retake. Pure OCR: it returns the text on the page or nothing — it never
invents content.
"""

import io

from google.cloud import vision
from google.oauth2 import service_account
from PIL import Image, ImageOps

# Google Vision reads small print better with a little more resolution than a
# generative vision model needs. 1600px long edge + JPEG q85 keeps a page well
# under the batch request-size limit while staying legible.
_MAX_EDGE_PX = 1600
_JPEG_QUALITY = 85

# Hard limit of the batchAnnotateImages endpoint.
_BATCH_SIZE = 16


def _build_client(credentials_info=None):
    """Make an ImageAnnotatorClient.

    credentials_info: the dict from st.secrets["gcp_service_account"]. When
    None, fall back to Application Default Credentials / the
    GOOGLE_APPLICATION_CREDENTIALS env var (used by local test scripts).
    """
    if credentials_info:
        creds = service_account.Credentials.from_service_account_info(
            dict(credentials_info)
        )
        return vision.ImageAnnotatorClient(credentials=creds)
    return vision.ImageAnnotatorClient()


def _downscale_to_jpeg(raw_bytes):
    """Shrink an uploaded image and re-encode as JPEG.

    Honours EXIF rotation before dropping EXIF, converts away from
    alpha/palette modes, caps the long edge, re-encodes. Any input format
    comes out as JPEG bytes.
    """
    img = Image.open(io.BytesIO(raw_bytes))
    img = ImageOps.exif_transpose(img)
    if img.mode not in ("RGB", "L"):
        img = img.convert("RGB")
    img.thumbnail((_MAX_EDGE_PX, _MAX_EDGE_PX), Image.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=_JPEG_QUALITY, optimize=True)
    return out.getvalue()


def _annotate(client, jpeg_list):
    """OCR a list of JPEG byte strings. Returns list[str] aligned to the
    input — empty string where Vision errored or found no text."""
    feature = vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)
    requests = [
        vision.AnnotateImageRequest(image=vision.Image(content=b), features=[feature])
        for b in jpeg_list
    ]
    texts = []
    for start in range(0, len(requests), _BATCH_SIZE):
        response = client.batch_annotate_images(
            requests=requests[start:start + _BATCH_SIZE]
        )
        for r in response.responses:
            if r.error.message:
                texts.append("")
            else:
                texts.append((r.full_text_annotation.text or "").strip())
    return texts


def transcribe_images(images, credentials_info=None):
    """OCR 1..N page images.

    images: list of file-like objects (Streamlit UploadedFile) supporting
    .read(). Returns:
      pages      — OCR text per image, in upload order ("" where OCR found nothing)
      jpegs      — downscaled JPEG bytes per image, same order (to send to the model)
      ocr_failed — 1-based positions where OCR returned nothing
    Raises ValueError on an empty list.
    """
    if not images:
        raise ValueError("transcribe_images needs at least one image")

    jpegs = [_downscale_to_jpeg(f.read()) for f in images]
    texts = _annotate(_build_client(credentials_info), jpegs)
    ocr_failed = [i for i, t in enumerate(texts, start=1) if not t]
    return {"pages": texts, "jpegs": jpegs, "ocr_failed": ocr_failed}
