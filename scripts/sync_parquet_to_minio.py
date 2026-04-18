import argparse
from pathlib import Path

import boto3
from botocore.client import Config


def create_s3_client(endpoint: str, access_key: str, secret_key: str):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="us-east-1",
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )


def ensure_bucket(client, bucket: str):
    buckets = {item["Name"] for item in client.list_buckets().get("Buckets", [])}
    if bucket not in buckets:
        client.create_bucket(Bucket=bucket)


def delete_prefix(client, bucket: str, prefix: str):
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        contents = page.get("Contents", [])
        if not contents:
            continue
        client.delete_objects(
            Bucket=bucket,
            Delete={"Objects": [{"Key": obj["Key"]} for obj in contents]},
        )


def upload_directory(client, local_dir: Path, bucket: str, prefix: str):
    files = sorted([path for path in local_dir.rglob("*") if path.is_file()])
    if not files:
        raise ValueError(f"No files found to upload from: {local_dir}")

    uploaded = 0
    for path in files:
        rel_path = path.relative_to(local_dir).as_posix()
        key = f"{prefix.rstrip('/')}/{rel_path}" if prefix else rel_path
        client.upload_file(str(path), bucket, key)
        uploaded += 1
        print(f"[upload] {path} -> s3://{bucket}/{key}")

    return uploaded


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--local-dir", required=True, help="Local parquet directory to upload")
    parser.add_argument("--minio-endpoint", required=True, help="MinIO endpoint URL")
    parser.add_argument("--access-key", required=True, help="MinIO access key")
    parser.add_argument("--secret-key", required=True, help="MinIO secret key")
    parser.add_argument("--bucket", required=True, help="Destination MinIO bucket")
    parser.add_argument("--prefix", required=True, help="Destination prefix inside bucket")
    args = parser.parse_args()

    local_dir = Path(args.local_dir)
    if not local_dir.exists():
        raise FileNotFoundError(f"Local directory not found: {local_dir}")

    client = create_s3_client(args.minio_endpoint, args.access_key, args.secret_key)
    ensure_bucket(client, args.bucket)
    delete_prefix(client, args.bucket, args.prefix)
    uploaded = upload_directory(client, local_dir, args.bucket, args.prefix)

    print("=" * 80)
    print("Uploaded parquet directory to MinIO successfully.")
    print(f"bucket: {args.bucket}")
    print(f"prefix: {args.prefix}")
    print(f"files_uploaded: {uploaded}")
    print("=" * 80)


if __name__ == "__main__":
    main()
