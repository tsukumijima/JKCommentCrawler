import asyncio
import configparser
import json
import os
import tempfile
import traceback
from datetime import datetime
from pathlib import Path

import anyio
import typer
from ndgr_client import NDGRClient, XMLCompatibleComment
from ndgr_client.niconico_oauth import NiconicoOAuthError, NiconicoProgramEndedError
from ndgr_client.utils import AsyncTyper
from pydantic import TypeAdapter
from rich import print
from rich.rule import Rule
from rich.style import Style

from jkcommentcrawler import NXClient, __version__
from jkcommentcrawler.notify import send_discord_report


app = AsyncTyper()


def version(value: bool):
    if value is True:
        typer.echo(f'JKCommentCrawler version {__version__}')
        raise typer.Exit()


@app.command(help='JKCommentCrawler: Nico Nico Jikkyo Comment Crawler')
async def main(
    channel_id: str = typer.Argument(
        help='コメントを収集する実況チャンネル。(ex: jk211) all を指定すると全チャンネルのコメントを収集する。'
    ),
    date: str = typer.Argument(help='コメントを収集する日付。(ex: 2024/08/05)'),
    save_dataset_structure_json: bool = typer.Option(
        False,
        '--save-dataset-structure-json',
        help='過去ログデータのフォルダ/ファイル構造を示す JSON ファイルを出力する。',
    ),
    force: bool = typer.Option(False, '-f', '--force', help='以前取得したログの方が文字数が多い場合でも上書きする。'),
    verbose: bool = typer.Option(False, '-v', '--verbose', help='詳細なログを表示する。'),
    version: bool = typer.Option(None, '--version', callback=version, is_eager=True, help='バージョン情報を表示する。'),
):

    async def write_text_atomically(path: anyio.Path, content: str) -> None:
        """
        書き込みを完了した一時ファイルで保存先を置き換える。
        書き込みの失敗や収集中の読み取りで、既存の過去ログが途中までの内容になるのを防ぐ。

        Args:
            path (anyio.Path): 保存先のファイルパス
            content (str): 保存する文字列
        """

        def write_file() -> None:
            # 同じファイルシステム内に一時ファイルを作り、書き込みが終わるまで保存先を変更しない
            output_path = Path(path)
            mode = output_path.stat().st_mode & 0o777 if output_path.exists() else 0o644
            temporary_path: Path | None = None
            try:
                with tempfile.NamedTemporaryFile(
                    mode='w', encoding='utf-8', dir=output_path.parent, prefix=f'.{output_path.name}.', delete=False
                ) as temporary_file:
                    temporary_path = Path(temporary_file.name)
                    temporary_file.write(content)
                    temporary_file.flush()
                    os.fsync(temporary_file.fileno())
                # ファイルを閉じてから置き換え、既存のアクセス権も引き継ぐ
                temporary_path.chmod(mode)
                os.replace(temporary_path, output_path)
            finally:
                # 保存に失敗した場合も一時ファイルだけを片付け、既存の過去ログは残す
                if temporary_path is not None:
                    temporary_path.unlink(missing_ok=True)

        await anyio.to_thread.run_sync(write_file)

    print(Rule(characters='=', style=Style(color='#E33157')))
    target_date = datetime.strptime(date, '%Y/%m/%d').date()
    if target_date > datetime.now().date():
        raise Exception('Target date is in the future.')

    # 設定読み込み
    config_ini = anyio.Path(__file__).parent.parent / 'JKCommentCrawler.ini'
    if not await config_ini.exists():
        raise Exception('JKCommentCrawler.ini not found. Copy from JKCommentCrawler.example.ini and edit it as needed.')
    config = configparser.ConfigParser()
    config.read(config_ini, encoding='utf-8')
    kakolog_dir: anyio.Path = await anyio.Path(config.get('Default', 'jkcomment_folder').rstrip('/')).resolve()
    # 認証方式は oauth または cookie の2択で、認証ファイルのパスはプロジェクトルートに固定する
    auth_method = config.get('Default', 'auth_method', fallback='oauth').strip().lower()
    if auth_method not in ('oauth', 'cookie'):
        raise ValueError(f"Invalid auth_method: '{auth_method}'. Must be 'oauth' or 'cookie'.")
    base_dir = Path(__file__).resolve().parent.parent
    niconico_oauth_file = base_dir / 'oauth.json' if auth_method == 'oauth' else None
    niconico_cookies_file = base_dir / 'cookies.json' if auth_method == 'cookie' else None

    # jikkyo_id に 'all' が指定された場合は全てのチャンネルをダウンロード
    if channel_id == 'all':
        jikkyo_channel_ids = NXClient.JIKKYO_CHANNEL_ID_LIST.copy()
    else:
        jikkyo_channel_ids = [channel_id]

    # 過去ログ収集対象のニコニコ実況チャンネルごとに
    comment_counts: dict[str, int] = {}
    failed_channels: list[str] = []
    unavailable_programs: list[str] = []
    # この実行の中だけで覚え、再認可が必要な OAuth 失敗を残りのニコ生番組へ繰り返さない
    oauth_failed = False
    for jikkyo_channel_id in jikkyo_channel_ids:
        # 最初の取得が失敗した場合は3回までリトライ
        for retry_count in range(4):
            try:
                print(
                    f'[{datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")}]\\[{jikkyo_channel_id}] '
                    f'Retrieve comments broadcast during {target_date.strftime("%Y/%m/%d")}.'
                )

                # 指定された日付に一部でも放送されたニコニコ生放送番組を取得
                ## NX-Jikkyo にはあるが本家ニコニコ実況に存在しない実況チャンネル (ex: jk141) では実行しない
                if oauth_failed is True:
                    nicolive_program_ids = []
                    print('Skipping retrieval of Nicolive comments as OAuth authentication already failed in this run.')
                elif jikkyo_channel_id not in NDGRClient.JIKKYO_CHANNEL_ID_MAP:
                    nicolive_program_ids = []
                    print(
                        f'Skipping retrieval of Nicolive comments as the channel {jikkyo_channel_id} does not exist on Nicolive.'
                    )
                else:
                    nicolive_program_ids = await NDGRClient.getProgramIDsOnDate(jikkyo_channel_id, target_date)
                    print(
                        f'Retrieving Nicolive comments from {len(nicolive_program_ids)} programs.'
                        + (f' ({", ".join(nicolive_program_ids)})' if len(nicolive_program_ids) > 0 else '')
                    )

                # 指定された日付に一部でも放送された NX-Jikkyo スレッドを取得
                nx_thread_ids = await NXClient.getThreadIDsOnDate(jikkyo_channel_id, target_date)
                print(
                    f'Retrieving NX-Jikkyo comments from {len(nx_thread_ids)} threads.'
                    + (f' ({", ".join(map(str, nx_thread_ids))})' if len(nx_thread_ids) > 0 else '')
                )
                print(Rule(characters='-', style=Style(color='#E33157')))

                # ダウンロードしたコメントを格納するリスト
                comments: list[XMLCompatibleComment] = []

                # ニコニコ生放送番組 ID ごとに
                for nicolive_program_id in nicolive_program_ids:
                    try:
                        # NDGRClient を初期化
                        async with NDGRClient(
                            nicolive_program_id, verbose=verbose, console_output=True, oauth_file=niconico_oauth_file
                        ) as ndgr_client:
                            # OAuth のトークン更新と保存は NDGRClient が行うため、ここでは Cookie 認証を選んだ場合の設定を行う
                            if auth_method == 'cookie':
                                assert niconico_cookies_file is not None
                                if not niconico_cookies_file.exists():
                                    raise FileNotFoundError(
                                        f'{niconico_cookies_file.name} not found. Place it in the project root.'
                                    )
                                cookies_dict = TypeAdapter(dict[str, str]).validate_json(
                                    await anyio.Path(niconico_cookies_file).read_text(encoding='utf-8')
                                )
                                if await ndgr_client.setCookies(cookies_dict) is False:
                                    raise ValueError(
                                        'The saved cookies have expired. Import fresh cookies or use OAuth.'
                                    )

                            # コメントをダウンロードしてリストに追加
                            ## タイムシフトの公開期間を過ぎた番組は OAuth の視聴 API が PROGRAM_ENDED を返すため、
                            ## その番組だけを取得対象から外し、同じ日の他の番組と NX-Jikkyo の収集は続行する
                            try:
                                ndgr_comments = await ndgr_client.downloadBackwardComments()
                            except NiconicoProgramEndedError:
                                unavailable_programs.append(nicolive_program_id)
                                print(
                                    f'Skipping {nicolive_program_id} as the program is no longer available (PROGRAM_ENDED).'
                                )
                                continue
                            comments.extend(
                                [NDGRClient.convertToXMLCompatibleComment(comment) for comment in ndgr_comments]
                            )
                    except NiconicoOAuthError:
                        # 再認可が必要な失敗はリトライしても直らないので、残りのニコ生番組は打ち切る
                        ## NX-Jikkyo と他チャンネルは取れるところまで取る
                        oauth_failed = True
                        print(
                            f'[{datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")}]\\[{jikkyo_channel_id}] '
                            'OAuth authentication failed. Continuing NX-Jikkyo retrieval and remaining channels.'
                        )
                        break

                # NX-Jikkyo スレッドごとに
                for nx_thread_id in nx_thread_ids:
                    # NXClient を初期化
                    async with NXClient(nx_thread_id, verbose=verbose, console_output=True) as nx_client:
                        # コメントをダウンロードしてリストに追加
                        comments.extend(await nx_client.downloadBackwardComments())

                # 指定された日付以外に投稿されたコメントを除外
                print(f'Total comments for {jikkyo_channel_id}: {len(comments)}')
                comments = [
                    comment
                    for comment in comments
                    if datetime.fromtimestamp(comment.date_with_usec).date() == target_date
                ]
                print(f'Excluding comments posted on dates other than {target_date.strftime("%Y/%m/%d")} ...')
                print(f'Final comments for {jikkyo_channel_id}: {len(comments)}')

                # コメント投稿日時昇順で並び替え
                ## ニコニコ実況と NX-Jikkyo のコメントを時系列でマージするためにこの処理が必要
                comments.sort(key=lambda comment: comment.date_with_usec)

                # {kakolog_dir}/{jikkyo_channel_id}/{date.year}/{date.strftime('%Y%m%d')}.nicojk に保存
                ## 取得できたコメントが1つもない場合は実行しない
                output_dir = kakolog_dir / jikkyo_channel_id / str(target_date.year)
                output_file = output_dir / f'{target_date.strftime("%Y%m%d")}.nicojk'
                existing_content = await output_file.read_text(encoding='utf-8') if await output_file.exists() else ''
                if len(comments) > 0:
                    await output_dir.mkdir(parents=True, exist_ok=True)

                    # コメントリストを XML 文字列に変換
                    xml_content = NDGRClient.convertToXMLString(comments)

                    # 既存の XML ファイルがあれば文字数を取得
                    existing_length = len(existing_content)

                    # コメントが1件も取得できていない場合は過去ログを保存しない
                    if len(xml_content) == 0:
                        print(f'Skipping log save for {target_date.strftime("%Y/%m/%d")} as there are 0 comments.')

                    # 既存のファイルの方が文字数が多い場合は過去ログを保存しない
                    elif existing_length > len(xml_content) and not force:
                        print(
                            f'Skipping log save as the previously retrieved log has more characters. '
                            f'(Previous: {existing_length} chars, Current: {len(xml_content)} chars)'
                        )

                    # 過去ログを保存
                    else:
                        # 既存のファイルの方が文字数が多いが、--force が指定されている場合は上書きする
                        if existing_length > len(xml_content) and force:
                            print(
                                f'The previously retrieved log has more characters, but overwriting as --force is specified. '
                                f'(Previous: {existing_length} chars, Current: {len(xml_content)} chars)'
                            )
                        # ファイルに書き込む
                        await write_text_atomically(output_file, xml_content)
                        print(f'Log saved to {output_file}.')

                # コメントが1件も取得できていない場合はスキップ
                elif len(comments) == 0:
                    print(
                        f'No comments found for {jikkyo_channel_id} on {target_date.strftime("%Y/%m/%d")}. Skipping ...'
                    )
                print(Rule(characters='=', style=Style(color='#E33157')))

                # 保存まで完了したチャンネルだけを成功として記録する
                comment_counts[jikkyo_channel_id] = len(comments)
                # 正常にダウンロードできたらループを抜ける
                break

            except Exception:
                if retry_count < 3:
                    # エラー発生時は3回までリトライ
                    print(
                        f'[{datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")}]\\[{jikkyo_channel_id}] '
                        f'Unexpected error occurred. Retrying ({retry_count + 1}/3) after 3 seconds ...'
                    )
                    print(traceback.format_exc())
                    await asyncio.sleep(3)
                else:
                    # リトライ失敗、このチャンネルはスキップして次の実況チャンネルへ
                    failed_channels.append(jikkyo_channel_id)
                    print(
                        f'[{datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")}]\\[{jikkyo_channel_id}] '
                        f'Unexpected error occurred. Retrying failed. Skipping ...'
                    )
                    print(traceback.format_exc())
                print(Rule(characters='=', style=Style(color='#E33157')))

    # 全チャンネルをダウンロードしたときは、各チャンネルごとの合計コメント数を表示
    if channel_id == 'all':
        print(f'Download finished: {len(comment_counts)} succeeded, {len(failed_channels)} failed.')
        for jikkyo_channel_id, count in comment_counts.items():
            print(f'{jikkyo_channel_id:>5}: {count:>5} comments')
        print(Rule(characters='=', style=Style(color='#E33157')))

    # --save-dataset-structure-json が指定されているときは、データセットの構造を JSON ファイルに保存
    if save_dataset_structure_json is True:

        async def get_directory_contents(
            directory_path: anyio.Path, nest: bool = False
        ) -> dict[str, dict[str, dict[str, None]]]:
            if not await directory_path.exists():
                raise FileNotFoundError(f'Directory "{directory_path}" does not exist.')
            data = {}
            # anyio.Path.iterdir() は非同期イテレータを返すため、リスト内包表記で収集してからソートする
            items = sorted([item async for item in directory_path.iterdir()])
            for item in items:
                # 保存途中の一時ファイルや Git の管理情報は公開用の一覧に含めない
                if item.name.startswith('.'):
                    continue
                if await item.is_dir() and (item.name.startswith('jk') or nest is True):
                    data[item.name] = await get_directory_contents(item, nest=True)
                elif await item.is_file() and nest is True:
                    data[item.name] = None
            return data

        dataset_structure = await get_directory_contents(kakolog_dir)
        dataset_structure_file = kakolog_dir / 'dataset_structure.json'
        await write_text_atomically(dataset_structure_file, json.dumps(dataset_structure, ensure_ascii=False, indent=4))
        print(f'Dataset structure saved to {dataset_structure_file}.')
        print(Rule(characters='=', style=Style(color='#E33157')))

    # 取得期限を過ぎた番組も最終結果に残し、部分的な取得を見落とさないようにする
    if unavailable_programs:
        print(f'Unavailable programs (PROGRAM_ENDED): {", ".join(dict.fromkeys(unavailable_programs))}')

    # 他のチャンネルの収集を終えてから失敗を返し、cron 側で正常完了と区別できるようにする
    if oauth_failed is True:
        print('OAuth authentication failed. Run the NDGRClient authorize command again.')
    if failed_channels:
        print(f'Download failed for channels: {", ".join(failed_channels)}')
    if oauth_failed is True or failed_channels:
        # 失敗の中身は収集側が知っているので、シェルを待たずにここで報告する
        details: list[str] = [f'過去ログ収集に失敗しました。\n日付: {target_date}']
        if oauth_failed is True:
            details.append('OAuth 認証に失敗しました。NDGRClient の authorize で oauth.json を作り直してください。')
        if failed_channels:
            details.append(f'失敗したチャンネル: {", ".join(failed_channels)}')
        try:
            send_discord_report('\n'.join(details))
        except Exception as ex:
            print(f'Failed to send Discord notification: {type(ex).__name__}')
        raise typer.Exit(code=1)


if __name__ == '__main__':
    app()
