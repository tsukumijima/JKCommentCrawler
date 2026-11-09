"""収集や公開の失敗を Discord へ報告する。"""

import argparse
import configparser
import socket
from pathlib import Path

import curl_cffi.requests as requests

from jkcommentcrawler import NXClient


ROOT = Path(__file__).resolve().parent.parent


def send_discord_report(message: str, run_log: Path | None = None) -> None:
    """
    ini の Webhook へ失敗内容を送る。
    収集本体からも、公開用シェルからも同じ関数を呼ぶ。

    Args:
        message (str): 通知本文 (ホスト名とメンションはこちらで付ける)
        run_log (Path | None): 添える実行ログ (省略可)
    """

    # JKCommentCrawler.ini から Webhook URL を取得
    config = configparser.ConfigParser(interpolation=None)
    config.read(ROOT / 'JKCommentCrawler.ini', encoding='utf-8')
    webhook_url = config.get('Default', 'discord_webhook_url', fallback='').strip()
    mention_to = config.get('Default', 'discord_mention_to', fallback='').strip()
    if webhook_url == '':
        print('Discord notifications are disabled. Set discord_webhook_url in JKCommentCrawler.ini to enable them.')
        return

    # ホスト名とログ末尾を添えて、Discord の本文上限に収める
    mention = f'<@{mention_to}> ' if mention_to else ''
    content = f'{mention}[{socket.gethostname()}] {message}'
    if run_log is not None and run_log.is_file():
        lines = run_log.read_text(encoding='utf-8', errors='replace').splitlines()
        if lines:
            log_tail = '\n'.join(lines[-15:])
            content += f'\n```\n{log_tail}\n```'

    # wait=true で Discord 側の保存完了を確認する
    # https://docs.discord.com/developers/resources/webhook#execute-webhook
    try:
        response = requests.post(
            webhook_url,
            params={'wait': 'true'},
            headers={'User-Agent': NXClient.USER_AGENT},
            json={
                'username': 'JKCommentCrawler',
                'content': content[:1900],
                'allowed_mentions': {'parse': [], 'users': [mention_to] if mention_to else []},
            },
            timeout=15,
        )
    except requests.RequestsError as ex:
        # 例外の文言には Webhook の URL が含まれるため、例外の種類だけを残す
        raise RuntimeError(f'Discord notification failed during transport. Reason: {type(ex).__name__}') from None
    if response.status_code != 200:
        # 応答本文や URL には Webhook の秘密が含まれるため、状態コードだけを残す
        raise RuntimeError(f'Discord notification failed. HTTP status: {response.status_code}')
    print('Discord notification sent.')


def main() -> None:
    """定期実行用シェルから、収集や公開の失敗を送る。"""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', default='starting')
    parser.add_argument('--exit-code', type=int, required=True)
    parser.add_argument('--log', type=Path, required=True)
    args = parser.parse_args()
    send_discord_report(
        f'JKCommentCrawler.sh が失敗しました。\n段階: {args.stage} / 終了コード: {args.exit_code}\nログ: {args.log}',
        run_log=args.log,
    )


if __name__ == '__main__':
    main()
