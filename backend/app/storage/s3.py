from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.config import Settings


class StorageError(RuntimeError):
    """Raised when an object storage operation cannot be completed."""


@dataclass(frozen=True)
class UploadTicket:
    url: str
    expires_at: datetime


@dataclass(frozen=True)
class StoredObject:
    size_bytes: int | None
    content_type: str | None
    etag: str | None


class S3Storage:
    def __init__(self, settings: Settings, client: Any | None = None) -> None:
        self.settings = settings
        self._client = client

    @property
    def client(self) -> Any:
        if self._client is None:
            try:
                self._client = boto3.client(
                    "s3",
                    endpoint_url=self.settings.storage_endpoint,
                    region_name=self.settings.storage_region,
                    aws_access_key_id=self.settings.storage_access_key,
                    aws_secret_access_key=self.settings.storage_secret_key,
                    config=Config(signature_version="s3v4"),
                )
            except (BotoCoreError, ClientError) as exc:
                raise StorageError("Unable to initialize object storage client") from exc
        return self._client

    def create_upload_ticket(self, key: str, content_type: str) -> UploadTicket:
        ttl = self.settings.storage_upload_url_ttl_seconds
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
        try:
            url = self.client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.settings.storage_bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=ttl,
                HttpMethod="PUT",
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Unable to create upload URL") from exc
        return UploadTicket(url=url, expires_at=expires_at)

    def head_object(self, key: str) -> StoredObject:
        try:
            response = self.client.head_object(Bucket=self.settings.storage_bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Unable to inspect object storage object") from exc
        return StoredObject(
            size_bytes=response.get("ContentLength"),
            content_type=response.get("ContentType"),
            etag=response.get("ETag"),
        )

    def download_file(self, key: str, destination: Path) -> None:
        try:
            self.client.download_file(self.settings.storage_bucket, key, str(destination))
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Unable to download object") from exc

    def upload_file(self, source: Path, key: str, content_type: str) -> None:
        try:
            self.client.upload_file(
                str(source),
                self.settings.storage_bucket,
                key,
                ExtraArgs={"ContentType": content_type},
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Unable to upload object") from exc

    def put_bytes(self, content: bytes, key: str, content_type: str) -> None:
        try:
            self.client.put_object(
                Bucket=self.settings.storage_bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Unable to upload object bytes") from exc

    def create_download_url(self, key: str) -> UploadTicket:
        ttl = self.settings.storage_download_url_ttl_seconds
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl)
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.settings.storage_bucket, "Key": key},
                ExpiresIn=ttl,
                HttpMethod="GET",
            )
        except (BotoCoreError, ClientError) as exc:
            raise StorageError("Unable to create download URL") from exc
        return UploadTicket(url=url, expires_at=expires_at)
