# JKCommentCrawler

ニコニコ生放送統合後の [ニコニコ実況](https://jk.nicovideo.jp/)・[NX-Jikkyo](https://nx-jikkyo.tsukumijima.net/) の過去ログを、実況チャンネル・日付ごとに一括収集して保存するツール。  
[Nekopanda](https://github.com/nekopanda) 氏がかつて公開していた旧ニコニコ実況の過去ログデータ一式と互換性のあるファイル・フォルダ構造で保存する。  
収集したデータは [Hugging Face (KakologArchives)](https://huggingface.co/datasets/KakologArchives/KakologArchives) で公開しており、[ニコニコ実況 過去ログ API](https://jikkyo.tsukumijima.net/) のデータソースにもなっている。

v2 ではコードが全面的に書き直されており、ニコニコ生放送の新メッセージサーバーからのコメント取得に [NDGRClient](https://github.com/tsukumijima/NDGRClient) (自作ライブラリ) を利用している。

## 技術スタック

- Python 3.11 系のみ対応 (`pyproject.toml` で `python = ">=3.11,<3.12"` に固定)
- パッケージマネージャは Poetry (`package-mode = false` のアプリケーションプロジェクト)
- CLI は Typer ベース (`jkcommentcrawler/__main__.py`)
- ニコニコ生放送側の通信は `ndgr-client` (`jkcommentcrawler/nx_client.py` が NX-Jikkyo 側のクライアント)
- Lint/Format は Ruff (シングルクォート、`line-length = 120`、`ruff check --fix .` / `ruff format .`)

## 主要コマンド

```bash
poetry install  # 依存関係のインストール

poetry run python -m jkcommentcrawler jk1 2024/08/05   # 単一チャンネルの過去ログ収集
poetry run python -m jkcommentcrawler all 2024/08/05   # 全チャンネルの過去ログ収集

poetry run task lint      # ruff check --fix .
poetry run task format    # ruff format .
```

実行前に `JKCommentCrawler.ini` (ニコニコの認証情報ファイル・過去ログ保存先フォルダ) の設定が必須。  
`JKCommentCrawler.example.ini` をコピーして使う。  
`JKCommentCrawler.ini` / `oauth.json` / `cookies.json` / `kakolog*` はいずれも Git 管理外 (`.gitignore` 参照)。

## この本番環境の依存関係と認証

認証情報は `JKCommentCrawler.ini` の `auth_method` で指定する認証方式 (`oauth` / `cookie`) に応じて、プロジェクトルートの `oauth.json` または `cookies.json` (いずれも Git 管理外) を参照する。  
OAuth トークンの更新・保存は NDGRClient が自動で行う。  
OAuth の失効 (再認可が必要な状態) は `NiconicoOAuthError` として、残りのニコニコ生放送の番組を同じ実行では集めずに NX-Jikkyo と他チャンネルの収集へ進める。復旧は NDGRClient の `authorize` コマンドで `oauth.json` を作り直す。  
`cookies.json` と ini 内の旧ログイン情報は使用していない。

## ディレクトリ構成

- `jkcommentcrawler/__main__.py`: CLI エントリーポイント、収集・保存ロジック本体
- `jkcommentcrawler/nx_client.py`: NX-Jikkyo 向けのコメント取得クライアント
- `JKCommentCrawler.ini`: 実行時設定 (Git 管理外、`.example.ini` からコピーして使う)
- `JKCommentCrawler.sh`: cron 実行用シェルスクリプト。過去ログ収集後、`kakolog/` を Hugging Face へ push するところまで含む
- `kakolog`: 過去ログ保存先へのシンボリックリンク。実体は `/mnt/ssd1/JKCommentCrawler-Kakolog/` にあり、JKCommentCrawler 本体とは別の独立した Git リポジトリ (Hugging Face の KakologArchives データセットと連携)

## kakolog データセットの Git LFS 運用

- `kakolog/` 配下は本体とは別の Git リポジトリで、Hugging Face の [KakologArchives](https://huggingface.co/datasets/KakologArchives/KakologArchives) データセットに直接 push している
- 過去ログ本体である `*.nicojk` ファイルは `kakolog/.gitattributes` で Git LFS 管理下に置かれている
- **このワークスペースは過去バージョンをローカルで checkout し直すことがなく、常に最新状態を Hugging Face に反映するだけの書き込み専用の同期用ワークスペースとして運用している。** そのため通常の Git LFS の保持ルールとは相性が悪く、作業ツリー上の `.nicojk` 実ファイルと、ローカル LFS キャッシュ (`.git/lfs/objects`) の二重保存がそのままディスク容量を圧迫する
  - 実際に `kakolog/.git` の実測サイズが211GBまで肥大化したことがあり、内訳を `git count-objects -vH` で確認すると通常の Git オブジェクトは 158MiB 程度しかなく、大半が `.git/lfs/objects` 配下のローカル LFS キャッシュだった
- **この構造を踏まえ、`JKCommentCrawler.sh` の末尾では `git push -f` が成功した場合にのみ `git lfs prune --force` を実行し、ローカル LFS キャッシュだけを削除する方針にしている** (作業ツリー上の `.nicojk` 実ファイルはそのまま残るため、ローカルバックアップとしての役割は保たれる)
  - `--verify-remote` 付きの prune はリモートとの突き合わせ件数が17万件規模まで積み上がると実行時間が長すぎて定常運用には向かないため、例外的にリモートの整合性そのものを疑う場面でだけ使う方針にしている
- Hugging Face 側の転送高速化のため git-xet (`lfs.customtransfer.xet.path` / `lfs.customtransfer.xet.args` に `git-xet` を設定済み) も併用しているが、これは転送方式の高速化であり、上記のローカル二重保存の構造自体を解消するものではない

## cron による定期実行に関する注意

- `JKCommentCrawler.sh` は cron から5分おき (`cron_minutes`) と、1日2回+予備の計4回 (`cron_daily`) で自動実行される運用になっている
- 実行中は `python -m jkcommentcrawler` によるコメント収集に加え、`kakolog/` 配下で `git add` / `git commit --amend` / `git push -f` / `git lfs prune --force` が動く
- **AI エージェントは、自分が起動していない git プロセスを異常だと誤認して kill してはいけない。** 過去に、cron 実行中の git プロセスを誤って kill してしまった事故が実際に発生している。プロセスが長時間動いている・CPU 使用率が高いといった見た目だけで「フリーズしている」と判断せず、まず cron による定期実行の途中である可能性を疑うこと
