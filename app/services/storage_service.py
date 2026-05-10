from __future__ import annotations

import os
import uuid
from pathlib import Path
from fastapi import UploadFile
from app.core.config import get_settings

settings = get_settings()


def _get_extension(filename: str) -> str:
    return Path(filename).suffix.lower()


def _generate_path(cotizacion_id: str, tipo: str, filename: str) -> str:
    ext = _get_extension(filename)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return f"cotizaciones/{cotizacion_id}/{tipo}/{unique_name}"


async def guardar_archivo(
    file: UploadFile,
    cotizacion_id: str,
    tipo: str,
) -> tuple[str, str]:
    """
    Guarda el archivo y devuelve (storage_path, url_descarga).
    Soporta backend local y S3/MinIO.
    """
    storage_path = _generate_path(cotizacion_id, tipo, file.filename)

    if settings.storage_backend == "s3":
        return await _guardar_s3(file, storage_path)
    else:
        return await _guardar_local(file, storage_path)


async def _guardar_local(file: UploadFile, storage_path: str) -> tuple[str, str]:
    full_path = Path(settings.storage_local_path) / storage_path
    full_path.parent.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    with open(full_path, "wb") as f:
        f.write(content)

    # URL relativa que el frontend puede usar vía el endpoint /files/
    url_descarga = f"/api/files/{storage_path}"
    return storage_path, url_descarga


async def _guardar_s3(file: UploadFile, storage_path: str) -> tuple[str, str]:
    """Requiere boto3: pip install boto3"""
    try:
        import boto3
        from botocore.client import Config

        s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
        )
        content = await file.read()
        s3.put_object(
            Bucket=settings.s3_bucket_name,
            Key=storage_path,
            Body=content,
            ContentType=file.content_type,
        )
        # URL pública (ajustar si el bucket es privado y se necesita presigned URL)
        base = settings.s3_endpoint_url or f"https://s3.amazonaws.com"
        url_descarga = f"{base}/{settings.s3_bucket_name}/{storage_path}"
        return storage_path, url_descarga
    except ImportError:
        raise RuntimeError("boto3 no instalado. Ejecuta: pip install boto3")


async def eliminar_archivo(storage_path: str):
    if settings.storage_backend == "s3":
        import boto3
        from botocore.client import Config
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4"),
        )
        # B2 mantiene versiones: hay que eliminar todas para borrar el archivo de verdad
        resp = s3.list_object_versions(Bucket=settings.s3_bucket_name, Prefix=storage_path)
        to_delete = [
            {"Key": v["Key"], "VersionId": v["VersionId"]}
            for v in resp.get("Versions", [])
        ] + [
            {"Key": m["Key"], "VersionId": m["VersionId"]}
            for m in resp.get("DeleteMarkers", [])
        ]
        if to_delete:
            s3.delete_objects(Bucket=settings.s3_bucket_name, Delete={"Objects": to_delete})
    else:
        full_path = Path(settings.storage_local_path) / storage_path
        if full_path.exists():
            full_path.unlink()
