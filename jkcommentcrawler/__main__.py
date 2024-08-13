
import configparser
import json
import typer
from datetime import datetime
from ndgr_client import NDGRClient, XMLCompatibleComment
from ndgr_client.utils import AsyncTyper
from pathlib import Path
from rich import print
from rich.rule import Rule
from rich.style import Style

from jkcommentcrawler import __version__


app = AsyncTyper()

def version(value: bool):
    if value is True:
        typer.echo(f'NX-Jikkyo version {__version__}')
        raise typer.Exit()

@app.command(help='JKCommentCrawler: Nico Nico Jikkyo Comment Crawler')
async def main(
    channel_id: str = typer.Argument(help='取得する実況チャンネル。(ex: jk211) all を指定すると全チャンネルのコメントを取得する。'),
    date: str = typer.Argument(help='取得する日付。(ex: 2020/12/19) 時刻情報は無視される。'),
    save_dataset_structure_json: bool = typer.Option(False, '--save-dataset-structure-json', help='過去ログデータのフォルダ/ファイル構造を示す JSON ファイルを出力する。'),
    force: bool = typer.Option(False, '-f', '--force', help='以前取得したログの方が文字数が多い場合でも上書きする。'),
    version: bool = typer.Option(None, '--version', callback=version, is_eager=True, help='バージョン情報を表示する。'),
):
    print(Rule(characters='=', style=Style(color='#E33157')))
    target_date = datetime.strptime(date, '%Y/%m/%d').date()

    # 設定読み込み
    config_ini = Path(__file__).parent.parent / 'JKCommentCrawler.ini'
    if not config_ini.exists():
        raise Exception('JKCommentCrawler.ini が存在しません。JKCommentCrawler.example.ini からコピーし、\n適宜設定を変更して JKCommentCrawler と同じ場所に配置してください。')
    config = configparser.ConfigParser()
    config.read(config_ini, encoding='UTF-8')
    kakolog_dir: Path = Path(config.get('Default', 'jkcomment_folder').rstrip('/') + 'test').resolve()
    niconico_mail: str = config.get('Default', 'nicologin_mail')
    niconico_password: str = config.get('Default', 'nicologin_password')

    # jikkyo_id に 'all' が指定された場合は全てのチャンネルをダウンロード
    if channel_id == 'all':
        jikkyo_channel_ids = [id for id in NDGRClient.JIKKYO_CHANNEL_ID_MAP.keys()]
    else:
        jikkyo_channel_ids = [channel_id]

    # 過去ログ収集対象のニコニコ実況チャンネルごとに実行
    await NDGRClient.updateJikkyoChannelIDMap()
    comment_counts: dict[str, int] = {}
    for jikkyo_channel_id in jikkyo_channel_ids:
        print(f'[{datetime.now().strftime("%Y/%m/%d %H:%M:%S.%f")}] Retrieve comments from {jikkyo_channel_id} broadcast during {target_date.strftime("%Y/%m/%d")}.')
        print(Rule(characters='-', style=Style(color='#E33157')))

        # ダウンロードしたコメントを格納するリスト
        comments: list[XMLCompatibleComment] = []

        # 指定された日付に一部でも放送された実況番組のコメントをすべてダウンロード
        nicolive_program_ids = await NDGRClient.getProgramIDsOnDate(jikkyo_channel_id, target_date)
        print(f'Retrieving Nicolive comments from {len(nicolive_program_ids)} programs. ({", ".join(nicolive_program_ids)})')
        for nicolive_program_id in nicolive_program_ids:

            # NDGRClient を初期化
            ndgr_client = NDGRClient(nicolive_program_id, verbose=False, console_output=True)

            # ニコニコアカウントにログイン (タイムシフト再生に必要)
            ## すでにログイン済みの Cookie が cookies.json にあれば再利用し、ない場合は新規ログインを行う
            cookie_json = kakolog_dir / 'cookie.json'
            if cookie_json.exists():
                with open(cookie_json, 'r', encoding='utf-8') as f:
                    cookies_dict = json.load(f)
                cookies_dict = await ndgr_client.login(cookies=cookies_dict)
                # もし None が返る場合はセッション切れの可能性があるので、再ログイン
                if cookies_dict is None:
                    cookies_dict = await ndgr_client.login(mail=niconico_mail, password=niconico_password)
                    if cookies_dict is None:
                        raise Exception('Failed to login to niconico.')
                    with open(cookie_json, 'w', encoding='utf-8') as f:
                        json.dump(cookies_dict, f)
            else:
                cookies_dict = await ndgr_client.login(mail=niconico_mail, password=niconico_password)
                if cookies_dict is None:
                    raise Exception('Failed to login to niconico.')
                with open(cookie_json, 'w', encoding='utf-8') as f:
                    json.dump(cookies_dict, f)

            # コメントをダウンロードしてリストに追加
            comments.extend([NDGRClient.convertToXMLCompatibleComment(comment) for comment in await ndgr_client.downloadBackwardComments()])

        # 指定された日付以外に投稿されたコメントを除外
        print(f'Total comments for {jikkyo_channel_id}: {len(comments)}')
        comments = [comment for comment in comments if datetime.fromtimestamp(comment.date_with_usec) == target_date]
        print(f'Excluding comments posted after {target_date.strftime("%Y/%m/%d")}...')
        print(f'Total comments for {jikkyo_channel_id}: {len(comments)}')
        comment_counts[jikkyo_channel_id] = len(comments)

        # {kakolog_dir}/{jikkyo_channel_id}/{date.year}/{date.strftime('%Y%m%d')}.nicojk に保存
        output_dir = kakolog_dir / jikkyo_channel_id / str(target_date.year)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f'{target_date.strftime("%Y%m%d")}.nicojk'
        with open(output_file, mode='w', encoding='utf-8') as f:
            f.write(NDGRClient.convertToXMLString(comments))
        print(f'Saved to {output_file}.')
        print(Rule(characters='=', style=Style(color='#E33157')))

    if channel_id == 'all':
        print('Download completed for all channels.')
        for jikkyo_channel_id, count in comment_counts.items():
            print(f'{jikkyo_channel_id:>5}: {count:>5} comments')
        print(Rule(characters='=', style=Style(color='#E33157')))


if __name__ == '__main__':
    app()
