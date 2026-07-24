"""Shared upload-validation helpers for any feature that accepts a PDF/JPEG/PNG file.

Extracted from ``medical_exam_service.py`` so the contract signed-upload path
(D4) can reuse the exact same size limit and magic-byte policy without the two
features' validation ever silently drifting apart.
"""

from fastapi import HTTPException, UploadFile, status

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024
UPLOAD_CHUNK_SIZE = 1024 * 1024

# Magic-byte signatures for the allowed MIME types, so validation checks actual
# file content rather than the client-supplied (and fully spoofable) Content-Type header.
MIME_SIGNATURES: dict[str, bytes] = {
    "application/pdf": b"%PDF-",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
}


def read_bounded(file: UploadFile, max_bytes: int = MAX_FILE_SIZE_BYTES) -> bytes:
    """Read the upload in chunks, rejecting early once it exceeds ``max_bytes``.

    Avoids buffering an unbounded request body into memory before the size
    check runs, since some callers (e.g. public endpoints) are reachable
    without full authentication.
    """
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = file.file.read(UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File exceeds the 10MB limit")
        chunks.append(chunk)
    return b"".join(chunks)


def validate_file(file: UploadFile, content: bytes, allowed_signatures: dict[str, bytes] = MIME_SIGNATURES) -> None:
    """Reject a file whose declared content type or magic bytes aren't an allowed match."""
    signature = allowed_signatures.get(file.content_type or "")
    if signature is None or not content.startswith(signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PDF, JPEG, or PNG files are accepted")
