#!/usr/bin/env python3
"""YouTubeチャンネルをポッドキャスト化する（GitHub Actions で毎日実行）。

音声ファイルは GitHub Release「episodes」に置き、
フィード(docs/feed.xml) とWebプレーヤー(docs/index.html) は GitHub Pages で配信する。

  python podcast.py update [--limit 10] [--keep 30]
"""
import argparse
import email.utils
import html
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

CHANNEL_URL = "https://www.youtube.com/@tsundoku-ch/videos"
SHOW_TITLE = "積読チャンネル（音声版）"
RELEASE_TAG = "episodes"

ROOT = os.path.dirname(os.path.abspath(__file__))
WORK_DIR = os.path.join(ROOT, "work")
DOCS = os.path.join(ROOT, "docs")
DB_PATH = os.path.join(DOCS, "episodes.json")
YTDLP_BASE = ["yt-dlp", "--js-runtimes", "node", "--no-warnings", "--retries", "10"]

REPO = os.environ.get("GITHUB_REPOSITORY", "OWNER/REPO")
IN_CI = os.environ.get("GITHUB_ACTIONS") == "true"
OWNER, NAME = REPO.split("/", 1)
PAGES_URL = "https://{}.github.io/{}/".format(OWNER.lower(), NAME)
AUDIO_BASE = "https://github.com/{}/releases/download/{}/".format(REPO, RELEASE_TAG)


def load_db():
    if os.path.exists(DB_PATH):
        with open(DB_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_db(db):
    with open(DB_PATH, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=1)


def gh(*args, check=True):
    return subprocess.run(["gh"] + list(args), capture_output=True, text=True, check=check)


def list_channel(limit):
    out = subprocess.run(
        YTDLP_BASE + ["--flat-playlist", "--playlist-end", str(limit),
                      "--print", "%(id)s\t%(title)s", CHANNEL_URL],
        capture_output=True, text=True, check=True).stdout
    return [line.split("\t", 1) for line in out.splitlines() if "\t" in line]


def download(vid):
    """音声を work/ep-<id>.m4a に取得してメタデータを返す。YouTube側が不安定なので数回試す。"""
    url = "https://www.youtube.com/watch?v=" + vid
    stem = "ep-" + vid  # 先頭が "-" のIDがあるので接頭辞を付ける
    info_path = os.path.join(WORK_DIR, stem + ".info.json")
    for attempt in range(4):
        r = subprocess.run(
            YTDLP_BASE + ["-f", "ba[ext=m4a]/ba", "--write-info-json",
                          "-o", os.path.join(WORK_DIR, stem + ".%(ext)s"), "--", vid],
            capture_output=True, text=True)
        audio = [f for f in os.listdir(WORK_DIR)
                 if f.startswith(stem + ".") and f.endswith((".m4a", ".webm", ".mp4"))]
        if r.returncode == 0 and audio and os.path.exists(info_path):
            break
        print("   再試行 ({}/3): {}".format(attempt + 1, (r.stderr.strip().splitlines() or [""])[-1]))
        time.sleep(5)
    else:
        return None
    with open(info_path, encoding="utf-8") as f:
        info = json.load(f)
    os.remove(info_path)
    fname = audio[0]
    return {
        "id": vid,
        "title": info.get("title", vid),
        "description": info.get("description", ""),
        "upload_date": info.get("upload_date", ""),
        "timestamp": info.get("timestamp"),
        "duration": info.get("duration") or 0,
        "thumbnail": info.get("thumbnail", ""),
        "file": fname,
        "size": os.path.getsize(os.path.join(WORK_DIR, fname)),
        "mime": "audio/mp4" if fname.endswith((".m4a", ".mp4")) else "audio/webm",
    }


def publish_audio(ep):
    path = os.path.join(WORK_DIR, ep["file"])
    if not IN_CI:
        print("   （ローカル実行のためアップロードは省略）")
        return True
    r = gh("release", "upload", RELEASE_TAG, path, "--clobber", "--repo", REPO, check=False)
    os.remove(path)
    if r.returncode != 0:
        print("   アップロード失敗:", r.stderr.strip())
    return r.returncode == 0


def ensure_release():
    if IN_CI and gh("release", "view", RELEASE_TAG, "--repo", REPO, check=False).returncode != 0:
        gh("release", "create", RELEASE_TAG, "--repo", REPO, "--title", "音声ファイル置き場",
           "--notes", "podcast.py が自動で管理しています")


def sorted_episodes(db):
    return sorted(db.values(), key=lambda e: (e.get("upload_date", ""), e.get("timestamp") or 0),
                  reverse=True)


def pub_date(ep):
    if ep.get("timestamp"):
        dt = datetime.fromtimestamp(ep["timestamp"], timezone.utc)
    elif ep.get("upload_date"):
        dt = datetime.strptime(ep["upload_date"], "%Y%m%d").replace(tzinfo=timezone.utc)
    else:
        dt = datetime.now(timezone.utc)
    return email.utils.format_datetime(dt)


def hms(sec):
    sec = int(sec or 0)
    return "{}:{:02d}:{:02d}".format(sec // 3600, sec % 3600 // 60, sec % 60)


def write_feed(db):
    esc = html.escape
    eps = sorted_episodes(db)
    items = []
    for ep in eps:
        items.append("""  <item>
    <title>{t}</title>
    <guid isPermaLink="false">yt:{id}</guid>
    <link>https://www.youtube.com/watch?v={id}</link>
    <pubDate>{d}</pubDate>
    <description>{desc}</description>
    <enclosure url="{url}" length="{size}" type="{mime}"/>
    <itunes:duration>{dur}</itunes:duration>
    <itunes:image href="{img}"/>
  </item>""".format(t=esc(ep["title"]), id=ep["id"], d=pub_date(ep), desc=esc(ep["description"]),
                    url=AUDIO_BASE + ep["file"], size=ep["size"], mime=ep["mime"],
                    dur=hms(ep["duration"]), img=esc(ep["thumbnail"])))
    feed = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">
<channel>
  <title>{title}</title>
  <link>{ch}</link>
  <language>ja</language>
  <description>YouTube「積読チャンネル」の音声を個人用にポッドキャスト化したフィード</description>
  <itunes:author>積読チャンネル</itunes:author>
  <itunes:block>Yes</itunes:block>
  <itunes:image href="{img}"/>
{items}
</channel>
</rss>
""".format(title=esc(SHOW_TITLE), ch=esc(CHANNEL_URL),
           img=esc(eps[0]["thumbnail"] if eps else ""), items="\n".join(items))
    with open(os.path.join(DOCS, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(feed)


def write_player(db):
    eps = []
    for ep in sorted_episodes(db):
        e = {k: ep[k] for k in ("id", "title", "upload_date", "duration", "thumbnail")}
        e["url"] = AUDIO_BASE + ep["file"]
        eps.append(e)
    with open(os.path.join(ROOT, "player_template.html"), encoding="utf-8") as f:
        tpl = f.read()
    page = (tpl.replace("__TITLE__", html.escape(SHOW_TITLE))
               .replace("__FEED_URL__", PAGES_URL + "feed.xml")
               .replace("__EPISODES__", json.dumps(eps, ensure_ascii=False).replace("</", "<\\/")))
    with open(os.path.join(DOCS, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)


def prune(db, keep):
    for ep in sorted_episodes(db)[keep:]:
        print(" 🗑 古い回を削除:", ep["title"])
        if IN_CI:
            gh("release", "delete-asset", RELEASE_TAG, ep["file"], "--yes", "--repo", REPO, check=False)
        del db[ep["id"]]


def cmd_update(args):
    os.makedirs(WORK_DIR, exist_ok=True)
    os.makedirs(DOCS, exist_ok=True)
    ensure_release()
    db = load_db()
    print("チャンネルの新着を確認中…")
    videos = list_channel(args.limit)
    new = [(vid, title) for vid, title in videos if vid not in db]
    print("新着 {} 件（確認した {} 件中）".format(len(new), len(videos)))
    failed = 0
    for vid, title in new:
        print(" ↓", title)
        ep = download(vid)
        if ep and publish_audio(ep):
            db[vid] = ep
            save_db(db)
        else:
            failed += 1
            print("   取得失敗。次回の実行で再試行します")
    if args.keep and len(db) > args.keep:
        prune(db, args.keep)
    save_db(db)
    write_feed(db)
    write_player(db)
    print("完了: {} エピソード / フィード: {}feed.xml".format(len(db), PAGES_URL))
    # 全部失敗したときは Actions を赤くして気づけるようにする
    return 1 if new and failed == len(new) else 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("update", help="新着を取得して公開")
    u.add_argument("--limit", type=int, default=10, help="チャンネルの最新何件を対象にするか")
    u.add_argument("--keep", type=int, default=30, help="公開しておく最大件数（0=無制限）")
    args = p.parse_args()
    return cmd_update(args)


if __name__ == "__main__":
    sys.exit(main())
