
import asyncio
import configparser
import json
import traceback
import typer
from datetime import datetime
from ndgr_client import NDGRClient, XMLCompatibleComment
from ndgr_client.utils import AsyncTyper
from pathlib import Path
from rich import print
from rich.rule import Rule
from rich.style import Style

from jkcommentcrawler import NXClient, __version__


app = AsyncTyper()

def version(value: bool):
    if value is True:
        typer.echo(f'JKCommentCrawler version {__version__}')
        raise typer.Exit()

@app.command(help='JKCommentCrawler: Nico Nico Jikkyo Comment Crawler')
async def main(
    channel_id: str = typer.Argument(help='コメントを収集する実況チャンネル。(ex: jk211) all を指定すると全チャンネルのコメントを収集する。'),
    date: str = typer.Argument(help='コメントを収集する日付。(ex: 2024/08/05)'),
    save_dataset_structure_json: bool = typer.Option(False, '--save-dataset-structure-json', help='過去ログデータのフォルダ/ファイル構造を示す JSON ファイルを出力する。'),
    force: bool = typer.Option(False, '-f', '--force', help='以前取得したログの方が文字数が多い場合でも上書きする。'),
    verbose: bool = typer.Option(False, '-v', '--verbose', help='詳細なログを表示する。'),
    version: bool = typer.Option(None, '--version', callback=version, is_eager=True, help='バージョン情報を表示する。'),
):
    print(Rule(characters='=', style=Style(color='#E33157')))
    target_date = datetime.strptime(date, '%Y/%m/%d').date()
    if target_date > datetime.now().date():
        raise Exception('Target date is in the future.')

    # 設定読み込み
    config_ini = Path(__file__).parent.parent / 'JKCommentCrawler.ini'
    if not config_ini.exists():
        raise Exception('JKCommentCrawler.ini not found. Copy from JKCommentCrawler.example.ini and edit it as needed.')
    config = configparser.ConfigParser()
    config.read(config_ini, encoding='utf-8')
    kakolog_dir: Path = Path(config.get('Default', 'jkcomment_folder').rstrip('/')).resolve()
    niconico_mail: str = config.get('Default', 'nicologin_mail')
    niconico_password: str = config.get('Default', 'nicologin_password')

    # jikkyo_id に 'all' が指定された場合は全てのチャンネルをダウンロード
    if channel_id == 'all':
        jikkyo_channel_ids = NXClient.JIKKYO_CHANNEL_ID_LIST.copy()
    else:
        jikkyo_channel_ids = [channel_id]

    # 過去ログ収集対象のニコニコ実況チャンネルごとに
    await NDGRClient.updateJikkyoChannelIDMap()
    comment_counts: dict[str, int] = {}
    for jikkyo_channel_id in jikkyo_channel_ids:

        # 3回までリトライ
        for retry_count in range(3):
            try:
                print(f'[{datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")}]\\[{jikkyo_channel_id}] '
                      f'Retrieve comments broadcast during {target_date.strftime("%Y/%m/%d")}.')

                # 指定された日付に一部でも放送されたニコニコ生放送番組を取得
                ## NX-Jikkyo にはあるが本家ニコニコ実況に存在しない実況チャンネル (ex: jk141) では実行しない
                if jikkyo_channel_id not in NDGRClient.JIKKYO_CHANNEL_ID_MAP:
                    nicolive_program_ids = []
                    print(f'Skipping retrieval of Nicolive comments as the channel {jikkyo_channel_id} does not exist on Nicolive.')
                else:
                    nicolive_program_ids = await NDGRClient.getProgramIDsOnDate(jikkyo_channel_id, target_date)
                    print(f'Retrieving Nicolive comments from {len(nicolive_program_ids)} programs.' +
                          (f' ({", ".join(nicolive_program_ids)})' if len(nicolive_program_ids) > 0 else ''))

                # 指定された日付に一部でも放送された NX-Jikkyo スレッドを取得
                nx_thread_ids = await NXClient.getThreadIDsOnDate(jikkyo_channel_id, target_date)
                print(f'Retrieving NX-Jikkyo comments from {len(nx_thread_ids)} threads.' +
                      (f' ({", ".join(map(str, nx_thread_ids))})' if len(nx_thread_ids) > 0 else ''))
                print(Rule(characters='-', style=Style(color='#E33157')))

                # ダウンロードしたコメントを格納するリスト
                comments: list[XMLCompatibleComment] = []

                # ニコニコ生放送番組 ID ごとに
                for nicolive_program_id in nicolive_program_ids:

                    # NDGRClient を初期化
                    ndgr_client = NDGRClient(nicolive_program_id, verbose=verbose, console_output=True)

                    # ニコニコアカウントにログイン (タイムシフト再生に必要)
                    ## すでにログイン済みの Cookie が cookies.json にあれば Cookie を再利用し、ない場合は新規ログインを行う
                    cookies_json = Path(__file__).parent.parent / 'cookies.json'
                    if cookies_json.exists():
                        with open(cookies_json, 'r', encoding='utf-8') as f:
                            cookies_dict = json.load(f)
                        cookies_dict = await ndgr_client.login(cookies=cookies_dict)
                        # もし None が返る場合はログインセッションが切れた可能性が高いので、メールアドレスとパスワードを指定して再ログインを実行
                        if cookies_dict is None:
                            cookies_dict = await ndgr_client.login(mail=niconico_mail, password=niconico_password)
                            if cookies_dict is None:
                                raise Exception('Failed to login to niconico.')
                            with open(cookies_json, 'w', encoding='utf-8') as f:
                                json.dump(cookies_dict, f)
                    else:
                        # cookies.json が存在しない場合は新規ログインを実行
                        cookies_dict = await ndgr_client.login(mail=niconico_mail, password=niconico_password)
                        if cookies_dict is None:
                            raise Exception('Failed to login to niconico.')
                        with open(cookies_json, 'w', encoding='utf-8') as f:
                            json.dump(cookies_dict, f)

                    # コメントをダウンロードしてリストに追加
                    comments.extend([
                        NDGRClient.convertToXMLCompatibleComment(comment)
                        for comment in await ndgr_client.downloadBackwardComments()
                    ])

                # NX-Jikkyo スレッドごとに
                for nx_thread_id in nx_thread_ids:

                    # NXClient を初期化
                    nx_client = NXClient(nx_thread_id, verbose=verbose, console_output=True)

                    # コメントをダウンロードしてリストに追加
                    comments.extend(await nx_client.downloadBackwardComments())

                # 指定された日付以外に投稿されたコメントを除外
                print(f'Total comments for {jikkyo_channel_id}: {len(comments)}')
                comments = [comment for comment in comments if datetime.fromtimestamp(comment.date_with_usec).date() == target_date]
                print(f'Excluding comments posted on dates other than {target_date.strftime("%Y/%m/%d")} ...')
                print(f'Final comments for {jikkyo_channel_id}: {len(comments)}')
                comment_counts[jikkyo_channel_id] = len(comments)

                # コメント投稿日時昇順で並び替え
                ## ニコニコ実況と NX-Jikkyo のコメントを時系列でマージするためにこの処理が必要
                comments.sort(key=lambda comment: comment.date_with_usec)

                # {kakolog_dir}/{jikkyo_channel_id}/{date.year}/{date.strftime('%Y%m%d')}.nicojk に保存
                ## 取得できたコメントが1つもない場合は実行しない
                if len(comments) > 0:
                    output_dir = kakolog_dir / jikkyo_channel_id / str(target_date.year)
                    output_dir.mkdir(parents=True, exist_ok=True)
                    output_file = output_dir / f'{target_date.strftime("%Y%m%d")}.nicojk'

                    # コメントリストを XML 文字列に変換
                    xml_content = NDGRClient.convertToXMLString(comments)

                    # 既存の XML ファイルがあれば文字数を取得
                    if output_file.exists():
                        with open(output_file, 'r', encoding='utf-8') as f:
                            existing_length = len(f.read())
                    else:
                        existing_length = 0

                    # コメントが1件も取得できていない場合は過去ログを保存しない
                    if len(xml_content) == 0:
                        print(f"Skipping log save for {target_date.strftime('%Y/%m/%d')} as there are 0 comments.")

                    # 既存のファイルの方が文字数が多い場合は過去ログを保存しない
                    elif existing_length > len(xml_content) and not force:
                        print(f'Skipping log save as the previously retrieved log has more characters. '
                              f'(Previous: {existing_length} chars, Current: {len(xml_content)} chars)')

                    # 過去ログを保存
                    else:
                        # 既存のファイルの方が文字数が多いが、--force が指定されている場合は上書きする
                        if existing_length > len(xml_content) and force:
                            print(f'The previously retrieved log has more characters, but overwriting as --force is specified. '
                                  f'(Previous: {existing_length} chars, Current: {len(xml_content)} chars)')
                        # ファイルに書き込む
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(xml_content)
                        print(f"Log saved to {output_file}.")

                # コメントが1件も取得できていない場合はスキップ
                elif len(comments) == 0:
                    print(f'No comments found for {jikkyo_channel_id} on {target_date.strftime("%Y/%m/%d")}. Skipping ...')
                print(Rule(characters='=', style=Style(color='#E33157')))

                # 正常にダウンロードできたらループを抜ける
                break

            except Exception:
                if retry_count < 3:
                    # エラー発生時は3回までリトライ
                    print(f'[{datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")}]\\[{jikkyo_channel_id}] '
                          f'Unexpected error occurred. Retrying ({retry_count + 1}/3) after 3 seconds ...')
                    print(traceback.format_exc())
                    await asyncio.sleep(3)
                else:
                    # リトライ失敗、このチャンネルはスキップして次の実況チャンネルへ
                    print(f'[{datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")}]\\[{jikkyo_channel_id}] '
                          f'Unexpected error occurred. Retrying failed. Skipping ...')
                    print(traceback.format_exc())
                print(Rule(characters='=', style=Style(color='#E33157')))

    # 全チャンネルをダウンロードしたときは、各チャンネルごとの合計コメント数を表示
    if channel_id == 'all':
        print('Download completed for all channels.')
        for jikkyo_channel_id, count in comment_counts.items():
            print(f'{jikkyo_channel_id:>5}: {count:>5} comments')
        print(Rule(characters='=', style=Style(color='#E33157')))

    # --save-dataset-structure-json が指定されているときは、データセットの構造を JSON ファイルに保存
    if save_dataset_structure_json is True:
        def get_directory_contents(directory_path: Path, nest: bool = False) -> dict[str, dict[str, dict[str, None]]]:
            if not directory_path.exists():
                raise FileNotFoundError(f'Directory "{directory_path}" does not exist.')
            data = {}
            for item in sorted(directory_path.iterdir()):
                if item.is_dir() and (item.name.startswith('jk') or nest is True):
                    data[item.name] = get_directory_contents(item, nest=True)
                elif item.is_file() and nest is True:
                    data[item.name] = None
            return data

        dataset_structure = get_directory_contents(kakolog_dir)
        with open(f'{kakolog_dir}/dataset_structure.json', 'w', encoding='utf-8') as f:
            json.dump(dataset_structure, f, ensure_ascii=False, indent=4)
        print(f'Dataset structure saved to {kakolog_dir}/dataset_structure.json.')
        print(Rule(characters='=', style=Style(color='#E33157')))


if __name__ == '__main__':
    app()
