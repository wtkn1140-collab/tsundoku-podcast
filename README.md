# 積読チャンネル 音声版

YouTube「積読チャンネル」の新着を毎朝6時に自動で音声化し、スマホのポッドキャストアプリで聴けるようにする仕組み。
GitHub（無料）上だけで動くので、パソコンの常時起動は不要。

## 初回セットアップ（1回だけ・約10分）

1. GitHub で新しいリポジトリを作る（例: `tsundoku-podcast`、**Public**）
2. このフォルダの中身をすべてアップロード（`.github` フォルダも含める）
3. リポジトリの **Settings → Pages** で
   Source =「Deploy from a branch」、Branch =「main」「/docs」→ Save
4. **Actions** タブ →「新着を取得」→ **Run workflow**（初回取得。10分ほどかかる）
5. スマホで `https://<ユーザー名>.github.io/tsundoku-podcast/` を開き、
   「Apple Podcasts で購読」をタップ

## 普段の使い方
- ポッドキャストアプリに新しい回が自動で届く。何もしなくてよい
- すぐ取得したいとき: GitHub アプリ → リポジトリ → Actions →「新着を取得」→ Run workflow
- 失敗するとGitHubから通知メールが届く（次の日に自動で再試行される）

## 設定を変えたいとき
- 時刻: `.github/workflows/update.yml` の `cron`（UTC表記。`0 21 * * *` = 日本時間6時）
- 残す件数: 同ファイルの `--keep 30`
