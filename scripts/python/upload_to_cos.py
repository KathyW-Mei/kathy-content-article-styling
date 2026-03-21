#!/usr/bin/env python3
"""
腾讯云 COS 上传脚本

使用官方 SDK 上传图片到 COS
"""

import argparse
import json
import sys
from pathlib import Path

from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client


def load_credentials(skill_dir: Path) -> dict:
    """加载 COS 凭证"""
    cred_path = skill_dir / "credentials" / "cos.json"
    if not cred_path.exists():
        raise FileNotFoundError(f"COS 凭证不存在: {cred_path}")
    return json.loads(cred_path.read_text(encoding="utf-8"))


def upload_file(
    client: CosS3Client,
    bucket: str,
    local_path: Path,
    remote_key: str
) -> str:
    """上传文件到 COS，返回公开 URL"""
    response = client.put_object_from_local_file(
        Bucket=bucket,
        LocalFilePath=str(local_path),
        Key=remote_key
    )
    return response.get('ETag', '')


def main():
    parser = argparse.ArgumentParser(description="上传文件到腾讯云 COS")
    parser.add_argument("--skill-dir", type=Path, required=True, help="Skill 目录")
    parser.add_argument("--local-path", type=Path, required=True, help="本地文件路径")
    parser.add_argument("--filename", type=str, required=True, help="目标文件名")
    parser.add_argument("--folder", type=str, default="images", help="目标文件夹")
    args = parser.parse_args()

    try:
        # 加载凭证
        creds = load_credentials(args.skill_dir)
        auth = creds.get("auth", {})

        secret_id = auth.get("secret_id")
        secret_key = auth.get("secret_key")
        region = auth.get("region")
        bucket = auth.get("bucket")
        folder = auth.get("images_folder", args.folder)

        if not all([secret_id, secret_key, region, bucket]):
            print(json.dumps({"ok": False, "err": "凭证不完整"}))
            sys.exit(1)

        # 初始化客户端
        config = CosConfig(
            Region=region,
            SecretId=secret_id,
            SecretKey=secret_key,
        )
        client = CosS3Client(config)

        # 检查本地文件
        if not args.local_path.exists():
            print(json.dumps({"ok": False, "err": f"文件不存在: {args.local_path}"}))
            sys.exit(1)

        # 上传
        remote_key = f"{folder}/{args.filename}"
        etag = upload_file(client, bucket, args.local_path, remote_key)

        url = f"https://{bucket}.cos.{region}.myqcloud.com/{remote_key}"

        result = {
            "ok": True,
            "url": url,
            "etag": etag,
            "key": remote_key
        }
        print(json.dumps(result, ensure_ascii=False))

    except Exception as e:
        print(json.dumps({"ok": False, "err": str(e)[:200]}))
        sys.exit(1)


if __name__ == "__main__":
    main()
