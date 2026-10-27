#!/usr/bin/env python3
"""Qualify required S3 semantics with scoped keys; input is private JSON on stdin."""

import json
import sys
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError


def expect_denied(client, bucket):
    try:
        client.head_bucket(Bucket=bucket)
    except ClientError as error:
        if error.response["ResponseMetadata"]["HTTPStatusCode"] == 403:
            return
        raise
    raise RuntimeError(f"Credential unexpectedly accesses forbidden bucket {bucket}")


def qualify(settings):
    if not settings["endpoint"].startswith("https://"):
        raise ValueError("An HTTPS endpoint with verified server identity is required")
    client = boto3.client(
        "s3", endpoint_url=settings["endpoint"], region_name=settings.get("region", "us-east-1"),
        aws_access_key_id=settings["access_key"], aws_secret_access_key=settings["secret_key"],
        verify=settings["ca_file"],
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"},
                      connect_timeout=10, read_timeout=60, retries={"max_attempts": 2}),
    )
    prefix = f".qualification/{uuid.uuid4().hex}/"
    for bucket in settings["buckets"]:
        client.head_bucket(Bucket=bucket)
        client.get_bucket_location(Bucket=bucket)
        key = prefix + "versions"
        first = client.put_object(Bucket=bucket, Key=key, Body=b"first")
        second = client.put_object(Bucket=bucket, Key=key, Body=b"second")
        first_id, second_id = first.get("VersionId"), second.get("VersionId")
        if not first_id or first_id == "null" or not second_id or first_id == second_id:
            raise RuntimeError(f"Versioned writes are not enabled for {bucket}")
        old = client.get_object(Bucket=bucket, Key=key, VersionId=first_id)["Body"].read()
        current = client.get_object(Bucket=bucket, Key=key)["Body"].read()
        if old != b"first" or current != b"second":
            raise RuntimeError("Version history or read-after-write is incorrect")
        versions = client.list_object_versions(Bucket=bucket, Prefix=key).get("Versions", [])
        if not {first_id, second_id}.issubset({entry["VersionId"] for entry in versions}):
            raise RuntimeError("ListObjectVersions omitted a committed version")
        client.copy_object(Bucket=bucket, Key=prefix + "copy", CopySource={
            "Bucket": bucket, "Key": key, "VersionId": first_id})
        if client.get_object(Bucket=bucket, Key=prefix + "copy", Range="bytes=0-3")["Body"].read() != b"firs":
            raise RuntimeError("Version-specific CopyObject or byte-range read failed")
        client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        client.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": key}, {"Key": prefix + "copy"}]})
        try:
            client.get_object(Bucket=bucket, Key=key)
        except ClientError as error:
            if error.response["ResponseMetadata"]["HTTPStatusCode"] != 404:
                raise
        else:
            raise RuntimeError("Deleting a versioned object did not hide its latest value")
        if client.get_object(Bucket=bucket, Key=key, VersionId=first_id)["Body"].read() != b"first":
            raise RuntimeError("DeleteObject lost the prior version")

    bucket = settings["buckets"][0]
    multipart_key = prefix + "multipart"
    upload = client.create_multipart_upload(Bucket=bucket, Key=multipart_key)["UploadId"]
    arguments = {"Bucket": bucket, "Key": multipart_key, "UploadId": upload}
    try:
        block = b"x" * (5 * 1024 * 1024)
        parts = []
        for number, body in enumerate((block, b"tail"), 1):
            result = client.upload_part(**arguments, PartNumber=number, Body=body)
            parts.append({"PartNumber": number, "ETag": result["ETag"]})
        if len(client.list_parts(**arguments).get("Parts", [])) != 2:
            raise RuntimeError("ListParts did not report both uploaded parts")
        client.list_multipart_uploads(Bucket=bucket, Prefix=prefix)
        client.complete_multipart_upload(**arguments, MultipartUpload={"Parts": parts})
        if client.get_object(Bucket=bucket, Key=multipart_key)["Body"].read() != block + b"tail":
            raise RuntimeError("Completed multipart content differs from its input")
    finally:
        try:
            client.abort_multipart_upload(**arguments)
        except ClientError as error:
            if error.response["Error"]["Code"] != "NoSuchUpload":
                raise
    aborted = client.create_multipart_upload(Bucket=bucket, Key=prefix + "abort")["UploadId"]
    client.abort_multipart_upload(Bucket=bucket, Key=prefix + "abort", UploadId=aborted)
    client.delete_object(Bucket=bucket, Key=multipart_key)
    for forbidden in settings.get("denied_buckets", []):
        expect_denied(client, forbidden)
    return {"buckets": settings["buckets"], "versioning": True, "multipart": True,
            "copy_range_delete": True, "denied_buckets": settings.get("denied_buckets", []), "prefix": prefix}


if __name__ == "__main__":
    print(json.dumps(qualify(json.load(sys.stdin))))
