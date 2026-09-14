#!/bin/bash

# Cron の設定例
## 毎日 00:01・00:15 (予備)・12:01・12:15 (予備) に実行
# 01 00 * * * sudo -u ubuntu /home/ubuntu/JKCommentCrawler/JKCommentCrawler.sh cron_daily
# 15 00 * * * sudo -u ubuntu /home/ubuntu/JKCommentCrawler/JKCommentCrawler.sh cron_daily
# 01 12 * * * sudo -u ubuntu /home/ubuntu/JKCommentCrawler/JKCommentCrawler.sh cron_daily
# 15 12 * * * sudo -u ubuntu /home/ubuntu/JKCommentCrawler/JKCommentCrawler.sh cron_daily
## 5分おきに実行
# */5 * * * * sudo -u ubuntu /home/ubuntu/JKCommentCrawler/JKCommentCrawler.sh cron_minutes

# 収集・保存・公開のどこで失敗しても、その終了コードを呼び出し元へ返す
set -Eeuo pipefail
umask 077

# 自身のスクリプトのフルパスを取得
SCRIPT_PATH="$(readlink -f "$0")"

# スクリプトが存在するディレクトリのパスを取得
SCRIPT_DIR="$(dirname "$SCRIPT_PATH")"
cd "${SCRIPT_DIR}"

# ログフォルダがなければ作成
LOG_DIR="${SCRIPT_DIR}/log"
LOG_DATE=$(date +%F)
RUN_MODE=${1:-normal}
case "$RUN_MODE" in
    cron_minutes|cron_daily|normal) ;;
    *) echo "Unknown run mode: $RUN_MODE" >&2; exit 2 ;;
esac
mkdir -p "${LOG_DIR}/${LOG_DATE}"

# 標準出力と標準エラーを実行単位でまとめ、次の実行で前回の記録が消えるのを防ぐ
RUN_LOG="${LOG_DIR}/${LOG_DATE}/${RUN_MODE}-$(date +%H%M%S)-$$.log"
exec >> "$RUN_LOG" 2>&1
START_SECONDS=$SECONDS
RUN_STAGE=starting
COLLECTION_EXIT=0

# 収集や公開の非ゼロ終了を Discord へ報告する
## 本体が通知処理に到達する前の失敗も報告するため、本体の詳細通知との重複を許容する
## 通知に失敗した場合も元の終了コードを返す
notify_run_failure() {
    local exit_code=$1
    if [[ "$exit_code" -eq 0 || "$exit_code" -eq 75 ]]; then
        return 0
    fi
    # 公開処理で移動した後も、プロジェクトルートから通知モジュールを起動する
    if ! (
        cd "$SCRIPT_DIR" && "${SCRIPT_DIR}/.venv/bin/python" -m jkcommentcrawler.notify \
            --stage "$RUN_STAGE" --exit-code "$exit_code" --log "$RUN_LOG"
    )
    then
        echo 'Failed to send Discord notification.'
    fi
}

finish_run() {
    local exit_code=$?
    notify_run_failure "$exit_code"
    printf '[%s] END mode=%s stage=%s exit_code=%s elapsed_seconds=%s\n' \
        "$(date --iso-8601=seconds)" "$RUN_MODE" "$RUN_STAGE" "$exit_code" "$((SECONDS - START_SECONDS))"
}
trap finish_run EXIT
trap 'printf "[%s] ERROR stage=%s line=%s\n" "$(date --iso-8601=seconds)" "$RUN_STAGE" "$LINENO"' ERR
trap 'exit 130' INT
trap 'exit 143' TERM
printf '[%s] START mode=%s pid=%s\n' "$(date --iso-8601=seconds)" "$RUN_MODE" "$$"

# 収集から push まで同じロックを保持し、5分を超えた処理と次の cron が重なるのを防ぐ
## 日次収集は毎時0分の収集と重なりやすいため、最大15分待って前日分の収集機会を確保する
lock_timeout=0
if [[ "$RUN_MODE" != cron_minutes ]]; then
    lock_timeout=900
fi
RUN_STAGE=lock
echo "Waiting for collection/publication lock (timeout=${lock_timeout}s)."
exec 9> "${LOG_DIR}/crawler.lock"
if ! flock -w "$lock_timeout" 9; then
    RUN_STAGE=skipped
    echo 'Another collection or publication is running. Skipping this run.'
    exit 75
fi
ln -sfn "${LOG_DATE}/$(basename "$RUN_LOG")" "${LOG_DIR}/latest-${RUN_MODE}.log"

# 前日以前の実行ログは圧縮し、今日を含む14日分だけを残す
## ロック取得後に実行するため、日付をまたいで動いている収集のログを圧縮することはない
RUN_STAGE=log_rotation
oldest_log_date=$(date -d '13 days ago' +%F)
for log_day_dir in "${LOG_DIR}"/20??-??-??; do
    [[ -d "$log_day_dir" ]] || continue
    log_day=$(basename "$log_day_dir")
    if [[ "$log_day" < "$oldest_log_date" ]]; then
        find "$log_day_dir" -maxdepth 1 -type f \( -name '*.log' -o -name '*.log.gz' \) -delete
        rmdir "$log_day_dir" 2>/dev/null || true
    elif [[ "$log_day" < "$LOG_DATE" ]]; then
        # 日付をまたいで書き込み中のログを潰さないよう、更新から5分以上経ったものだけ圧縮する
        find "$log_day_dir" -maxdepth 1 -type f -name '*.log' -mmin +5 -exec gzip -- {} +
    fi
done

# 最新の日次ログなどが圧縮された場合は、参照先も圧縮済みファイルへ更新する
for latest_log in "${LOG_DIR}"/latest-*.log; do
    [[ -L "$latest_log" ]] || continue
    latest_target=$(readlink "$latest_log")
    if [[ ! -e "$latest_log" && -f "${LOG_DIR}/${latest_target}.gz" ]]; then
        ln -sfn "${latest_target}.gz" "$latest_log"
    fi
done

# 障害時に、実際に使われた通信ライブラリの版を確認できるようにする
"${SCRIPT_DIR}/.venv/bin/python" -u -c \
    'import sys; from importlib.metadata import version; print("Python {}, ndgr-client {}, curl-cffi {}, NX HTTP/1.1".format(sys.version.split()[0], version("ndgr-client"), version("curl-cffi")))'
current_time=$(date +"%Y/%m/%d %H:%M")
RUN_STAGE=collection

# JKCommentCrawler を実行
# 一部チャンネルの失敗でも保存できた分は公開する
# Cron（5分ごと）
if [[ $RUN_MODE = 'cron_minutes' ]]; then

    # 今日分の JKCommentCrawler を実行
    echo 'JKCommentCrawler.sh (Cron minutes)'
    "${SCRIPT_DIR}/.venv/bin/python" -u -m jkcommentcrawler all "$(date +%Y/%m/%d)" --save-dataset-structure-json \
        || COLLECTION_EXIT=$?

# Cron（1日ごと）
elif [[ $RUN_MODE = 'cron_daily' ]]; then

    # 前日分の JKCommentCrawler を実行（取りこぼし防止）
    ## --force パラメータを付けると、以前取得したログよりサイズが小さくても強制的に保存する
    ## ニコ生の実況番組の放送終了後にスパム判定されたコメント (特に AA) がごっそり削除されることがあり、
    ## それによって新しいログが保存されなくなる事態を避ける
    echo 'JKCommentCrawler.sh (Cron daily)'
    "${SCRIPT_DIR}/.venv/bin/python" -u -m jkcommentcrawler all "$(date -d '-1 day' +%Y/%m/%d)" --save-dataset-structure-json --force \
        || COLLECTION_EXIT=$?

# 通常実行
else
    echo 'JKCommentCrawler.sh (Normal)'
    "${SCRIPT_DIR}/.venv/bin/python" -u -m jkcommentcrawler all "$(date +%Y/%m/%d)" --save-dataset-structure-json \
        || COLLECTION_EXIT=$?
fi
if [[ "$COLLECTION_EXIT" -eq 0 ]]; then
    echo 'Collection completed successfully.'
else
    echo "Collection finished with errors (exit_code=${COLLECTION_EXIT}). Publishing saved logs."
fi

# Hugging Face (KakologArchives) に commit & push する
# デフォルトでは前回のコミットに上書き追記し、コミット数を削減する
# 前回のコミットメッセージが Add kakolog until 20xx/xx/xx 00:00 or 12:00 の時だけ、前回コミットを上書きせずそのままコミットする
# こうすることで、1日に2回は必ずコミットされるようになる
RUN_STAGE=commit
cd "${SCRIPT_DIR}/kakolog/"
last_commit_message=$(git log -1 --pretty=%B)
# 強制終了で残った保存途中の一時ファイルは、コミット対象から外す
git add -- . ':(exclude,glob)**/.*.nicojk.*' ':(exclude,glob).dataset_structure.json.*'
if [[ $last_commit_message == *"00:00" ]] || [[ $last_commit_message == *"12:00" ]]; then
    git commit -m "Add kakolog until ${current_time}"
else
    git commit -m "Add kakolog until ${current_time}" --amend --date=now
fi
# Hugging Face への push が完了した場合だけ、ローカルの LFS キャッシュを削除する
## この作業ディレクトリでは過去バージョンをローカルで checkout しないため、
## LFS オブジェクトはリモートに送信済みなら都度ダウンロードできる履歴として扱う
RUN_STAGE=push
if git push -f; then
    # 現在 checkout 中のファイルに対応する LFS キャッシュも削除対象に含める
    ## 作業ツリー上の .nicojk 実ファイルは残るため、ローカルバックアップとしての役割は維持される
    RUN_STAGE=lfs_prune
    git lfs prune --force
else
    echo 'Failed to push kakolog to Hugging Face.'
    exit 1
fi
RUN_STAGE=completed
if [[ "$COLLECTION_EXIT" -ne 0 ]]; then
    exit "$COLLECTION_EXIT"
fi
