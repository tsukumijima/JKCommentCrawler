# JKCommentCrawler

ニコニコ生放送統合後の [ニコニコ実況](https://jk.nicovideo.jp/)・[NX-Jikkyo](https://nx-jikkyo.tsukumijima.net/) の過去ログを、実況チャンネル・日付ごとに一括収集して保存するツール。  
[Nekopanda](https://github.com/nekopanda) 氏がかつて公開していた旧ニコニコ実況の過去ログデータ一式と互換性のあるファイル・フォルダ構造で保存する。  
収集したデータは [Hugging Face (KakologArchives)](https://huggingface.co/datasets/KakologArchives/KakologArchives) で公開しており、[ニコニコ実況 過去ログ API](https://jikkyo.tsukumijima.net/) のデータソースにもなっている。

v2 ではコードが全面的に書き直されており、ニコニコ生放送の新メッセージサーバーからのコメント取得に [NDGRClient](https://github.com/tsukumijima/NDGRClient) (自作ライブラリ) を利用している。

## 設計思想

最優先はフェイルセーフである。365日分の過去ログを欠かさず残すことが目的なので、不測の事態が起きても、取れるものを取り切ってから失敗を返す。  
チャンネルごと、取得元ごと、番組ごとに、取れるところまで進める。

収集自体はステートレスである。毎回その日のコメントを取り直し、前回の取得結果を差分の入力にはしない。  
差分利用は、欠けた側を正だと思い込んで上書きする事故の元になる。

保存時に既存ファイルの方が大きいときは上書きしないのは、短い取得で長いログを壊さないためであり、前回内容を次の取得に使うことではない。  
`--force` を明示した場合は、ニコ生側の削除に合わせて短い結果で置き換えられる。  
日次実行ではこのオプションを自動で付け、手動で過去日を再収集する場合にも指定できる。  
OAuth 失効や番組の公開終了でニコ生の取得を省略したチャンネルは、`--force` 指定時も既存のサイズ保護を適用する。

実行の成否は、その実行の終了コードとログだけで読む。成功時刻や通知済み障害をファイルに残して crontab の間隔と突き合わせる判定は持たない。  
定期実行の起動は cron の責務であり、このツールが見るのは起動した実行の成否だけである。

認証ファイルのパスはプロジェクトルートの `oauth.json` / `cookies.json` に固定する。実行ごとに探せる場所を増やさない。

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

実行前に `JKCommentCrawler.ini` (過去ログ保存先フォルダと任意の Discord Webhook) の設定が必須。  
`JKCommentCrawler.example.ini` をコピーして使う。  
`JKCommentCrawler.ini` / `oauth.json` / `cookies.json` / `kakolog*` はいずれも Git 管理外 (`.gitignore` 参照)。

## この本番環境の依存関係と認証

認証方式は `JKCommentCrawler.ini` の `auth_method` (`oauth` / `cookie`) で選び、ファイルはプロジェクトルートの `oauth.json` または `cookies.json` を参照する。  
OAuth トークンの更新・保存は NDGRClient が自動で行う。  
`cookies.json` は Cookie 認証を選択した場合に使用する。

OAuth の失効 (再認可が必要な状態) は `NiconicoOAuthError` になる。  
ニコ生の残りの番組は打ち切り、NX-Jikkyo と他チャンネルの収集は続ける。  
実行末尾で終了コード1を返し、収集本体から Discord にも報告する。  
復旧は NDGRClient の `authorize` コマンドで `oauth.json` を作り直す。

## ディレクトリ構成

- `jkcommentcrawler/__main__.py`: CLI エントリーポイント、収集・保存ロジック本体
- `jkcommentcrawler/nx_client.py`: NX-Jikkyo 向けのコメント取得クライアント
- `jkcommentcrawler/notify.py`: 収集や公開の失敗を Discord へ報告する
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

- NX-Jikkyo 向けの通信は、スレッド一覧とコメント取得の両方を HTTP/1.1 に固定している。ニコニコ生放送向けの通信設定は NDGRClient に従う
- 実行ログは `log/YYYY-MM-DD/cron_minutes-HHMMSS-PID.log` などへ標準出力・標準エラーをまとめて保存する。当日分は平文、前日以前は gzip 圧縮し、今日を含む14日分を保持する
- 直近の収集ログは `log/latest-cron_minutes.log` と `log/latest-cron_daily.log` で参照できる。末尾の `END` に処理段階・終了コード・所要時間を記録する
- `log/crawler.lock` の排他ロックを収集から公開完了まで保持する。重複した5分ごとの cron は独立したログを残して終了コード75で終了する。日次収集と通常実行は最大15分待つため、毎時0分の収集と重なっても前日分を収集できる。手動で保存先を更新する際も `flock log/crawler.lock <command>` で同じロックを取得する
- チャンネル単位の再試行が尽きても残りのチャンネルを収集し、最後に失敗したチャンネル名と終了コード1を返す。保存できたチャンネルは、同じ実行の公開へ進める
- `JKCommentCrawler.sh` は cron から5分おき (`cron_minutes`) と、1日2回+予備の計4回 (`cron_daily`) で自動実行される運用になっている
- 実行中は `python -m jkcommentcrawler` によるコメント収集に加え、`kakolog/` 配下で `git add` / `git commit --amend` / `git push -f` / `git lfs prune --force` が動く
- **AI エージェントは、自分が起動していない git プロセスを異常だと誤認して kill してはいけない。** 過去に、cron 実行中の git プロセスを誤って kill してしまった事故が実際に発生している。プロセスが長時間動いている・CPU 使用率が高いといった見た目だけで「フリーズしている」と判断せず、まず cron による定期実行の途中である可能性を疑うこと
- 稼働中の `JKCommentCrawler.sh` を更新する際は、別ファイルへ書き出して構文を検査した後に同じファイルシステム内で置き換える。実行中のファイルを直接書き換えると、Bash が読み取りを再開した位置で構文エラーになることがある

収集の失敗 (OAuth 失効やチャンネル単位の取得失敗) は `jkcommentcrawler` 本体が `discord_webhook_url` へ報告する。  
`JKCommentCrawler.sh` は、収集や公開の非ゼロ終了を報告する。  
本体が通知処理に到達する前の失敗も報告するため、本体の詳細通知との重複を許容する。

`discord_mention_to` があればメンションする。通知に失敗しても収集と公開は続ける。  
ロック待ちのスキップ (75) は想定どおりの待機なので報告しない。

## 検証

通信処理を変えたときは、対象日・対象チャンネルから実際に収集し、取得元のスキップ、保存件数、XML の日付・順序を確認する。
