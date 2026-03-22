#!/usr/bin/env python3
"""
publish_to_notion.py — Upload images to Discord CDN, then create Notion page.

Usage:
    python3 publish_to_notion.py --run-dir /path/to/run --skill-dir /path/to/skill
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_discord_bot_token(oc_config):
    token = oc_config.get("channels", {}).get("discord", {}).get("token")
    if token:
        return token
    raise ValueError("No Discord bot token found in openclaw.json channels.discord.token")


def get_channel_id_for_agent(oc_config, agent_id):
    for b in oc_config.get("bindings", []):
        if b.get("agentId") == agent_id:
            return (b.get("match", {})
                     .get("peer", {})
                     .get("id"))
    return None


def upload_image_to_discord(img_path, bot_token, channel_id):
    filename = Path(img_path).name
    api_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {"Authorization": f"Bot {bot_token}"}
    with open(img_path, "rb") as f:
        resp = requests.post(
            api_url, headers=headers,
            files={"files[0]": (filename, f, "image/png")}
        )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Discord upload failed ({resp.status_code}): {resp.text[:200]}"
        )
    data = resp.json()
    return data["attachments"][0]["url"]


# ── Notion helpers ────────────────────────────────────────────────────────────

NOTION_API = "https://api.notion.com/v1"


def notion_headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


def _rich_text(content):
    return [{"type": "text", "text": {"content": content[:2000]}}]


def heading_block(level, content):
    t = f"heading_{level}"
    return {"type": t, t: {"rich_text": _rich_text(content)}}


def paragraph_block(content):
    return {"type": "paragraph", "paragraph": {"rich_text": _rich_text(content)}}


def image_block(url):
    return {"type": "image", "image": {"type": "external", "external": {"url": url}}}


def divider_block():
    return {"type": "divider", "divider": {}}


def md_to_blocks(md_text, url_map):
    """Convert markdown to Notion blocks. url_map: filename → CDN URL."""
    blocks = []
    for line in md_text.splitlines():
        s = line.rstrip()
        if not s:
            continue
        # Image reference: ![alt](filename or url)
        m = re.match(r"!\[([^\]]*)\]\(([^\)]+)\)", s)
        if m:
            _, src = m.groups()
            # url_map keys are filenames; src may be a filename or full URL
            url = url_map.get(Path(src).name, src)
            if url.startswith("http"):
                blocks.append(image_block(url))
            continue
        if s.startswith("### "):
            blocks.append(heading_block(3, s[4:]))
        elif s.startswith("## "):
            blocks.append(heading_block(2, s[3:]))
        elif s.startswith("# "):
            blocks.append(heading_block(1, s[2:]))
        elif s.startswith("---"):
            blocks.append(divider_block())
        else:
            blocks.append(paragraph_block(s))
    return blocks


def create_notion_page(token, database_id, title, blocks, plain_text, platform="小红书"):
    payload = {
        "parent": {"database_id": database_id},
        "properties": {
            "标题": {"title": [{"text": {"content": title}}]},
            "笔记内容": {"rich_text": [{"text": {"content": plain_text[:2000]}}]},
            "平台": {"select": {"name": platform}},
            "状态": {"select": {"name": "draft"}},
        },
        "children": blocks[:100],
    }
    resp = requests.post(
        f"{NOTION_API}/pages",
        headers=notion_headers(token),
        json=payload,
    )
    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Notion create page failed ({resp.status_code}): {resp.text[:300]}"
        )
    page = resp.json()
    page_id = page["id"]
    # Append remaining blocks in batches of 100
    for i in range(100, len(blocks), 100):
        batch = blocks[i:i + 100]
        requests.patch(
            f"{NOTION_API}/blocks/{page_id}/children",
            headers=notion_headers(token),
            json={"children": batch},
        )
    return page


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--skill-dir", required=True)
    parser.add_argument("--platform", default="小红书",
                        help="平台名称，需与 Notion 平台字段选项一致")
    args = parser.parse_args()

    run_dir = Path(args.run_dir)
    skill_dir = Path(args.skill_dir)

    config = load_json(run_dir / "state/config.json")
    notion_creds = load_json(skill_dir / "credentials/notion.json")

    oc_path = Path("/home/node/.openclaw/openclaw.json")
    if not oc_path.exists():
        oc_path = Path.home() / ".openclaw/openclaw.json"
    oc_config = load_json(oc_path)

    notion_token = notion_creds["auth"]["token"]
    database_id = notion_creds["target"]["database_id"]
    bot_token = get_discord_bot_token(oc_config)

    channel_id = get_channel_id_for_agent(oc_config, "xhs")
    if not channel_id:
        print(json.dumps({"ok": False, "error": "xhs channel not found in openclaw.json bindings"}))
        sys.exit(1)

    # ── 1. Upload images to Discord CDN ───────────────────────────────────────
    img_dir = run_dir / "step03-generate"
    url_map = {}
    uploads = []
    pngs = sorted(img_dir.glob("*.png"))

    print(f"Uploading {len(pngs)} images to Discord CDN...", file=sys.stderr)
    for png in pngs:
        try:
            cdn_url = upload_image_to_discord(png, bot_token, channel_id)
            url_map[png.name] = cdn_url
            uploads.append({"local": png.name, "url": cdn_url, "ok": True})
            print(f"  ✓ {png.name} → {cdn_url}", file=sys.stderr)
        except Exception as e:
            uploads.append({"local": png.name, "url": None, "ok": False, "error": str(e)})
            print(f"  ✗ {png.name}: {e}", file=sys.stderr)

    (run_dir / "step04-upload").mkdir(exist_ok=True)
    urls_data = {
        "storage_mode": "discord_cdn",
        "uploads": uploads,
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
        "total": len(uploads),
        "success": sum(1 for u in uploads if u["ok"]),
    }
    with open(run_dir / "step04-upload/urls.json", "w", encoding="utf-8") as f:
        json.dump(urls_data, f, ensure_ascii=False, indent=2)

    # ── 2. Read article markdown ──────────────────────────────────────────────
    output_dir = run_dir / "output"
    md_files = sorted(output_dir.glob("*.md")) if output_dir.exists() else []
    if md_files:
        article_path = md_files[0]
    else:
        article_path = Path(config["document"]["path"])

    with open(article_path, encoding="utf-8") as f:
        article_md = f.read()

    # ── 3. Create Notion page ─────────────────────────────────────────────────
    blocks = md_to_blocks(article_md, url_map)
    plain_text = re.sub(r"!\[.*?\]\(.*?\)", "", article_md)
    plain_text = re.sub(r"\n{3,}", "\n\n", plain_text).strip()

    title = config["document"]["title"]
    platform = args.platform
    print(f"Creating Notion page: {title} [{platform}]", file=sys.stderr)

    page = create_notion_page(notion_token, database_id, title, blocks, plain_text, platform)
    notion_url = page.get("url", "")
    print(f"  ✓ {notion_url}", file=sys.stderr)

    result = {
        "ok": True,
        "notion_url": notion_url,
        "total_images": len(uploads),
        "uploaded_images": sum(1 for u in uploads if u["ok"]),
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
