
import httpx
from datetime import date, datetime
from ndgr_client import XMLCompatibleComment
from pathlib import Path
from pydantic import BaseModel, TypeAdapter
from rich import print
from rich.rule import Rule
from rich.style import Style
from typing import Any, Literal

from jkcommentcrawler import __version__


class NXClient:
    """
    NX-Jikkyo メッセージサーバーのクライアント実装
    NX-Jikkyo の WebSocket API は 2024/06/08 以前のニコニコ生放送の API 仕様と互換性がある
    このクラスの設計は意図的に NDGRClient クラスに似せてある
    ref: https://github.com/tsukumijima/NX-Jikkyo
    ref: https://github.com/tsukumijima/NDGRClient
    """

    # NX-Jikkyo 通信時の User-Agent
    USER_AGENT = f'JKCommentCrawler/{__version__}'

    # NX-Jikkyo で運用されているニコニコ実況チャンネル ID のリスト (2024/08/15 時点)
    JIKKYO_CHANNEL_ID_LIST: list[str] = [
        'jk1',
        'jk2',
        'jk4',
        'jk5',
        'jk6',
        'jk7',
        'jk8',
        'jk9',
        'jk10',
        'jk11',
        'jk12',
        'jk101',
        'jk103',
        'jk141',
        'jk151',
        'jk161',
        'jk171',
        'jk181',
        'jk191',
        'jk192',
        'jk193',
        'jk211',
        'jk222',
        'jk236',
        'jk252',
        'jk260',
        'jk263',
        'jk265',
        'jk333',
    ]


    def __init__(self, thread_id: int, verbose: bool = False, console_output: bool = False, log_path: Path | None = None) -> None:
        """
        NXClient のコンストラクタ

        Args:
            thread_id (int): NX-Jikkyo のスレッド ID
            verbose (bool, default=False): 詳細な動作ログを出力するかどうか
            console_output (bool, default=False): 動作ログをコンソールに出力するかどうか
            log_path (Path | None, default=None): 動作ログをファイルに出力する場合のパス (show_log と併用可能)
        """

        self.thread_id = thread_id
        self.verbose = verbose
        self.show_log = console_output
        self.log_path = log_path

        # httpx の非同期 HTTP クライアントのインスタンスを作成
        self.httpx_client = httpx.AsyncClient(headers={'User-Agent': self.USER_AGENT}, follow_redirects=True)


    @classmethod
    async def getThreadIDsOnDate(cls, jikkyo_channel_id: str, date: date) -> list[int]:
        """
        指定した日付に少なくとも一部が放送されている/放送された NX-Jikkyo スレッドの ID を取得する

        Args:
            jikkyo_channel_id (str): ニコニコ実況互換のチャンネル ID
            date (date): NX-Jikkyo のスレッド (通常毎日 04:00 ~ 翌日 04:00) を取得する日付

        Returns:
            list[int]: 指定した日付に少なくとも一部が放送されている/放送された NX-Jikkyo スレッドの ID のリスト (放送開始日時昇順)

        Raises:
            ValueError: ニコニコ実況互換のチャンネル ID が指定されていない場合
            httpx.HTTPStatusError: NX-Jikkyo API へのリクエストに失敗した場合
        """

        if jikkyo_channel_id.startswith('jk') is False:
            raise ValueError(f'Invalid jikkyo_channel_id: {jikkyo_channel_id}')

        class ThreadInfo(BaseModel):
            id: int
            start_at: datetime
            end_at: datetime
            title: str
            description: str
            status: str

        # クラスメソッドから self.httpx_client にはアクセスできないため、新しい httpx.AsyncClient を作成している
        async with httpx.AsyncClient(headers={'User-Agent': cls.USER_AGENT}, follow_redirects=True) as client:

            # スレッド情報取得 API にリクエスト
            ## 実況チャンネル ID に紐づく過去全スレッドの情報を取得できる
            response = await client.get(f'https://nx-jikkyo.tsukumijima.net/api/v1/channels/{jikkyo_channel_id}/threads')
            response.raise_for_status()
            threads = TypeAdapter(list[ThreadInfo]).validate_json(response.content)

        # 指定された日付に放送されているスレッドをフィルタリングし、その ID をリストで返す
        threads = [
            thread for thread in threads
            if thread.start_at.date() <= date <= thread.end_at.date()
        ]

        # ID を放送開始日時が早い順に並べ替えてから返す
        threads.sort(key=lambda x: x.start_at)
        return [thread.id for thread in threads]


    async def downloadBackwardComments(self, ignore_nicolive_comments: bool = True) -> list[XMLCompatibleComment]:
        """
        NX-Jikkyo メッセージサーバーから過去に投稿されたコメントを遡ってダウンロードする

        Args:
            ignore_nicolive_comments (bool, default=True): ニコニコ実況に投稿され NX-Jikkyo にリアルタイムマージされたコメントを除外するかどうか

        Returns:
            list[XMLCompatibleComment]: 過去に投稿されたコメントのリスト (投稿日時昇順)

        Raises:
            httpx.HTTPStatusError: HTTP リクエストが失敗した場合
            AssertionError: 解析に失敗した場合
        """

        class CommentResponse(BaseModel):
            id: int
            thread_id: int
            no: int
            vpos: int
            date: datetime
            mail: str
            user_id: str
            premium: bool
            anonymity: bool
            content: str

        class ThreadResponse(BaseModel):
            id: int
            channel_id: str
            start_at: datetime
            end_at: datetime
            duration: int
            title: str
            description: str
            status: Literal['ACTIVE', 'UPCOMING', 'PAST']
            comments: list[CommentResponse]

        # スレッド取得 API にリクエスト
        response = await self.httpx_client.get(f'https://nx-jikkyo.tsukumijima.net/api/v1/threads/{self.thread_id}')
        response.raise_for_status()
        thread: ThreadResponse = TypeAdapter(ThreadResponse).validate_json(response.content)
        self.print(f'Title:  {thread.title} [{thread.status}] ({thread.id})')
        self.print(f'Period: {thread.start_at.strftime("%Y-%m-%d %H:%M:%S")} ~ {thread.end_at.strftime("%Y-%m-%d %H:%M:%S")} '
                   f'({thread.end_at - thread.start_at}h)')
        self.print(Rule(characters='-', style=Style(color='#E33157')), verbose_log=True)

        # 基本投稿日時昇順でソートされているはずだが、念のためここでもソートする
        ## この後の処理で date は秒単位とミリ秒単位に分割するため、ここでソートしておかないと色々面倒
        thread.comments.sort(key=lambda x: x.date)

        # NX-Jikkyo から取得したコメントデータをニコニコ XML 互換コメント形式に変換する
        xml_compatible_comments: list[XMLCompatibleComment] = []
        for comment in thread.comments:
            xml_comment = XMLCompatibleComment(
                # スレッド ID は NX-Jikkyo のスレッド ID を文字列化したものをそのまま入れる
                thread = str(comment.thread_id),
                no = comment.no,
                vpos = comment.vpos,
                date = int(comment.date.timestamp()),
                date_usec = int((comment.date.timestamp() % 1) * 1000000),
                mail = comment.mail,
                user_id = comment.user_id,
                premium = 1 if comment.premium is True else None,
                anonymity = 1 if comment.anonymity is True else None,
                content = comment.content,
            )
            # ニコニコ実況に投稿され NX-Jikkyo にリアルタイムマージされたコメントを除外する
            if ignore_nicolive_comments is True and comment.user_id.startswith('nicolive:') is True:
                xml_comment.user_id = xml_comment.user_id.replace('nicolive:', '')
                self.print(str(xml_comment), verbose_log=True)
                self.print(f'[yellow]Skipped a comment from nicolive.[/yellow]', verbose_log=True)
            else:
                self.print(str(xml_comment), verbose_log=True)
                xml_compatible_comments.append(xml_comment)
            self.print(Rule(characters='-', style=Style(color='#E33157')), verbose_log=True)

        self.print(f'Retrieved a total of {len(xml_compatible_comments)} comments.')
        self.print(Rule(characters='-', style=Style(color='#E33157')))
        return xml_compatible_comments


    def print(self, *args: Any, verbose_log: bool = False, **kwargs: Any) -> None:
        """
        NXClient の動作ログをコンソールやファイルに出力する

        Args:
            verbose_log (bool, default=False): 詳細な動作ログかどうか (指定された場合、コンストラクタで verbose が指定された時のみ出力する)
        """

        # このログが詳細な動作ログで、かつ詳細な動作ログの出力が有効でない場合は何もしない
        if verbose_log is True and self.verbose is False:
            return

        # 有効ならログをコンソールに出力する
        if self.show_log is True:
            print(*args, **kwargs)

        # ログファイルのパスが指定されている場合は、ログをファイルにも出力
        if self.log_path is not None:
            with self.log_path.open('a') as f:
                print(*args, **kwargs, file=f)
