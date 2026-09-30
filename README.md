# 積読チャンネル 音声版

YouTube「積読チャンネル」の新着を音声化し、スマホのポッドキャストアプリで聴けるようにする仕組み。

- **取得**: Mac が起きている間、2時間ごとに自動で新着を確認（launchd）
- **配信**: GitHub（音声 = Release「episodes」、フィードとプレーヤー = GitHub Pages）
- 取得を Mac で行うのは、YouTube が GitHub などのサーバーからのアクセスをボット判定で拒否するため

## スマホで聴く
- プレーヤー: https://wtkn1140-collab.github.io/tsundoku-podcast/
- フィード: https://wtkn1140-collab.github.io/tsundoku-podcast/feed.xml
  （プレーヤーの「Apple Podcasts で購読」から登録できる）

## Mac 側
- 自動実行: `~/Library/LaunchAgents/com.tsundoku.podcast.plist` → `run.sh`
- ログ: `logs/update.log`
- 手動で今すぐ取得: `./run.sh`
- 自動実行を止める: `launchctl bootout gui/$(id -u) ~/Library/LaunchAgents/com.tsundoku.podcast.plist`
- `bin/` の yt-dlp と gh は git 管理外（yt-dlp は実行のたびに自動更新）

## 設定
- 残す件数: `run.sh` の `--keep 30`（超えた古い回は GitHub からも削除）
- 確認間隔: plist の `StartInterval`（秒）
