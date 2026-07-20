"""Thin client wrapping OCI Object Storage for document metadata-only persistence.

The application never stores file bytes in the database; callers upload
directly to Object Storage and persist only the resulting storage key
(see ``Document.storage_key``).
"""

from functools import lru_cache

import oci

from app.core.config import get_settings


@lru_cache
def _client() -> "oci.object_storage.ObjectStorageClient":
    """Build a cached OCI Object Storage client from app settings."""
    settings = get_settings()
    config = {
        "tenancy": settings.oci_tenancy_ocid,
        "user": settings.oci_user_ocid,
        "fingerprint": settings.oci_fingerprint,
        "key_content": settings.oci_private_key,
        "region": settings.oci_region,
    }
    return oci.object_storage.ObjectStorageClient(config)


def upload_document(key: str, content: bytes, content_type: str) -> None:
    """Upload document bytes to the configured bucket under ``key``."""
    settings = get_settings()
    _client().put_object(
        settings.oci_bucket_namespace, settings.documents_bucket_name, key, content, content_type=content_type
    )


def delete_document(key: str) -> None:
    """Delete a previously uploaded document by its storage key."""
    settings = get_settings()
    _client().delete_object(settings.oci_bucket_namespace, settings.documents_bucket_name, key)
