
import json
import lxml.etree as ET
import os
import pickle
import requests
import shutil
import sys
import traceback
import websocket
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import Any


# バージョン情報
__version__ = '1.9.0'


class JKComment:

    # User-Agent
    user_agent = f'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36 JKCommentCrawler/{__version__}'

    # 実況 ID とチャンネル/コミュニティ ID の対照表
    jikkyo_channel_table = {
        'jk1': {'type': 'channel', 'id': 'ch2646436', 'name': 'NHK総合'},
        'jk2': {'type': 'channel', 'id': 'ch2646437', 'name': 'NHK Eテレ'},
        'jk4': {'type': 'channel', 'id': 'ch2646438', 'name': '日本テレビ'},
        'jk5': {'type': 'channel', 'id': 'ch2646439', 'name': 'テレビ朝日'},
        'jk6': {'type': 'channel', 'id': 'ch2646440', 'name': 'TBSテレビ'},
        'jk7': {'type': 'channel', 'id': 'ch2646441', 'name': 'テレビ東京'},
        'jk8': {'type': 'channel', 'id': 'ch2646442', 'name': 'フジテレビ'},
        'jk9': {'type': 'channel', 'id': 'ch2646485', 'name': 'TOKYO MX'},
        'jk10': {'type': 'community', 'id': 'co5253063', 'name': 'テレ玉'},
        'jk11': {'type': 'community', 'id': 'co5215296', 'name': 'tvk'},
        'jk12': {'type': 'community', 'id': 'co5359761', 'name': 'チバテレビ'},
        'jk101': {'type': 'channel', 'id': 'ch2647992', 'name': 'NHK BS1'},
        'jk103': {'type': 'community', 'id': 'co5175227', 'name': 'NHK BSプレミアム'},
        'jk141': {'type': 'community', 'id': 'co5175341', 'name': 'BS日テレ'},
        'jk151': {'type': 'community', 'id': 'co5175345', 'name': 'BS朝日'},
        'jk161': {'type': 'community', 'id': 'co5176119', 'name': 'BS-TBS'},
        'jk171': {'type': 'community', 'id': 'co5176122', 'name': 'BSテレ東'},
        'jk181': {'type': 'community', 'id': 'co5176125', 'name': 'BSフジ'},
        'jk191': {'type': 'community', 'id': 'co5251972', 'name': 'WOWOW PRIME'},
        'jk192': {'type': 'community', 'id': 'co5251976', 'name': 'WOWOW LIVE'},
        'jk193': {'type': 'community', 'id': 'co5251983', 'name': 'WOWOW CINEMA'},
        'jk211': {'type': 'channel',   'id': 'ch2646846', 'name': 'BS11'},
        'jk222': {'type': 'community', 'id': 'co5193029', 'name': 'BS12'},
        'jk236': {'type': 'community', 'id': 'co5296297', 'name': 'BSアニマックス'},
        'jk252': {'type': 'community', 'id': 'co5683458', 'name': 'WOWOW PLUS'},
        'jk260': {'type': 'community', 'id': 'co5682554', 'name': 'BS松竹東急'},
        'jk263': {'type': 'community', 'id': 'co5682551', 'name': 'BSJapanext'},
        'jk265': {'type': 'community', 'id': 'co5682548', 'name': 'BSよしもと'},
        'jk333': {'type': 'community', 'id': 'co5245469', 'name': 'AT-X'},
    }

    def __init__(self, jikkyo_id, date, nicologin_mail, nicologin_password):

        # 実況 ID
        self.jikkyo_id = jikkyo_id

        # 取得する日付
        self.date = date

        # メールアドレス・パスワード
        self.nicologin_mail = nicologin_mail
        self.nicologin_password = nicologin_password

    # コメントセッションに接続してコメントを取得する
    # objformat は xml または json のいずれか
    def getComment(self, objformat='xml'):

        # 番組単体でコメントを取得する
        def getCommentOne(live_id):

            # 視聴セッションへの接続情報を取得
            watchsession_info = self.__getWatchSessionInfo(live_id)

            # 開始・終了時間
            begintime = watchsession_info['program']['beginTime']
            endtime = watchsession_info['program']['endTime']
            print('-' * shutil.get_terminal_size().columns)
            print(f"番組タイトル: {watchsession_info['program']['title']} ({watchsession_info['program']['nicoliveProgramId']})")
            print(f"番組開始時刻: {datetime.fromtimestamp(begintime).strftime('%Y/%m/%d %H:%M:%S')}  " +
                  f"番組終了時刻: {datetime.fromtimestamp(endtime).strftime('%Y/%m/%d %H:%M:%S')}")

            # コメントセッションへの接続情報を取得
            commentsession_info = self.__getCommentSessionInfo(watchsession_info)

            # 取得を開始する時間
            if endtime > datetime.now().astimezone().timestamp():
                # 番組終了時刻が現在時刻よりも後（＝現在放送中）の場合は、when を現在時刻のタイムスタンプに設定
                # when を現在時刻より後に設定するとバグるのか、数分～数時間前以前のログしか返ってこないため
                when = datetime.now().astimezone().timestamp()
            else:
                # 番組終了時刻・取得終了時刻のどちらか小さい方を選択
                date_235959_timestamp = (self.date + timedelta(hours=23, minutes=59, seconds=59)).astimezone().timestamp()
                when = min(endtime, date_235959_timestamp)

            # Sec-WebSocket-Protocol が重要
            try:
                commentsession = websocket.create_connection(commentsession_info['messageServer']['uri'], timeout=15, header={
                    'User-Agent': JKComment.user_agent,
                    'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits',
                    'Sec-WebSocket-Protocol': 'msg.nicovideo.jp#json',
                    'Sec-WebSocket-Version': '13',
                })
            except ConnectionResetError as ex1:
                raise WebSocketError(f"コメントセッションへの接続がリセットされました。({ex1})")
            except websocket.WebSocketConnectionClosedException as ex2:
                raise WebSocketError(f"コメントセッションへの接続が閉じられました。({ex2})")
            except websocket.WebSocketTimeoutException as ex3:
                raise WebSocketError(f"コメントセッションへの接続がタイムアウトしました。({ex3})")
            except Exception as ex4:
                print(traceback.format_exc(), file=sys.stderr)
                raise WebSocketError(f"コメントセッションへの接続に失敗しました。({ex4})")

            # コメント情報を入れるリスト
            chat = []

            while True:

                # コメントリクエストを送る
                commentsession.send(json.dumps([
                    {'ping': {'content': 'rs:0'}},
                    {'ping': {'content': 'ps:0'}},
                    {'ping': {'content': 'pf:0'}},
                    {'ping': {'content': 'rf:0'}},
                    {
                        'thread': {
                            'thread': commentsession_info['threadId'],  # スレッド ID
                            'version': '20061206',
                            'when': when + 1,  # 基準にする時間 (UNIXTime)  +1 するのは取りこぼしをなくすため
                            'res_from': -1000,  # 基準にする時間（通常は生放送の最後）から 1000 コメント遡る
                            'with_global': 1,
                            'scores': 1,
                            'nicoru': 0,
                            'waybackkey': '',  # waybackkey は WebSocket だといらないらしい
                        }
                    },
                ]))

                # コメント情報を入れるリスト（1000 コメントごとの小分け）
                chat_child = []

                # 1000 コメント取得できるまでループ
                while True:

                    # 5 秒以上でタイムアウト
                    commentsession.settimeout(5)

                    # 受信データを取得
                    response_raw = 'Unknown'
                    try:
                        response_raw = commentsession.recv()
                        response = json.loads(response_raw)
                    # タイムアウトした（＝これ以上コメントは返ってこない）のでループを抜ける
                    except websocket.WebSocketTimeoutException:
                        break
                    # JSON デコードに失敗
                    except json.decoder.JSONDecodeError:
                        raise WebSocketError(f"受信データ '{response_raw}' を JSON としてデコードできません。")
                    except Exception as ex:
                        print(traceback.format_exc(), file=sys.stderr)
                        raise WebSocketError(f"コメントセッションからの受信中に予期せぬエラーが発生しました。({ex})")

                    # スレッド情報
                    if 'thread' in response:

                        # 最後のコメ番
                        if 'last_res' in response['thread']:
                            last_res = response['thread']['last_res']
                        else:
                            last_res = -1  # last_res が存在しない場合は -1 に設定

                    # コメント情報
                    if 'chat' in response:

                        # コメントを追加
                        chat_child.append(response)

                        # 最後のコメ番なら while ループを抜ける
                        if last_res == response['chat']['no']:
                            break

                # last_res が -1 → 最後のコメ番自体が存在しない → コメントが一度も存在しないスレッド
                # chat_child が空の場合も同様に判断する
                if last_res == -1 or len(chat_child) == 0:
                    # 処理を中断して抜ける
                    print(f"{self.date.strftime('%Y/%m/%d')} 中の合計 {len(chat)} 件のコメントを取得しました。")
                    break

                # when を取得した最後のコメントのタイムスタンプ + 1 で更新
                # + 1 しないと取りこぼす可能性がある
                when = int(chat_child[0]['chat']['date']) + float('0.' + str(chat_child[0]['chat']['date_usec'])) + 1

                # コメントの重複を削除
                if len(chat) > 0:

                    last_comeban = chat_child[-1]['chat']['no']  # 今回取得の最後のコメ番
                    first_comeban = chat[0]['chat']['no']  # 前回取得の最初のコメ番

                    # 今回取得の最後のコメ番が前回取得の最初のコメ番よりも小さくなるまでループ
                    while (last_comeban >= first_comeban):

                        # 重複分を 1 つずつ削除
                        if len(chat_child) > 0:
                            chat_child.pop(-1)
                        else:
                            break

                        # 最後のコメ番を更新
                        if len(chat_child) > 0:
                            last_comeban = chat_child[-1]['chat']['no']
                        else:
                            break

                    # chat_child が空の場合
                    # 1000 個取得しようとしてるのにコメントが何も入っていないのはおかしいので、全て取得したものとみなす
                    if len(chat_child) == 0:
                        break

                # chat に chat_child の内容を取得
                # 最後のコメントから遡るので、さっき取得したコメントは既に取得したコメントよりも前に連結する
                chat = chat_child + chat

                # 標準出力を上書きする
                # 参考: https://hacknote.jp/archives/51679/
                print('\r' + f"{self.date.strftime('%Y/%m/%d')} 中の合計 {str(len(chat))} 件のコメントを取得しました。", end='')

                # コメ番が 1 ならすべてのコメントを取得したと判断して抜ける
                if int(chat[0]['chat']['no']) == 1:
                    print()  # 改行を出力
                    break

                # 最初のコメントのタイムスタンプが取得開始より前なら抜ける（無駄に取得しないように）]
                if int(chat[0]['chat']['date']) < self.date.timestamp():
                    print()  # 改行を出力
                    break

            # コメントセッションを閉じる
            commentsession.close()

            print(f"コメントを {watchsession_info['program']['title']} から取得しました。")

            # 番組単体で取得したコメントを返す
            return chat

        # フォーマット
        objformat = objformat.lower()
        if objformat != 'xml' and objformat != 'json':
            raise FormatError('不正なフォーマットです。')

        # 番組 ID らを取得
        # 指定された日付内に放送された全ての番組からコメントを取得するので複数入ることがある
        live_ids = self.__getNicoLiveID(self.jikkyo_id, self.date)
        if live_ids is None:
            raise LiveIDError('番組 ID を取得できませんでした。')

        # コメントを取得
        chat = []
        for live_id in live_ids:
            chat = chat + getCommentOne(live_id)

        print('-' * shutil.get_terminal_size().columns)
        print(f"合計コメント数: {str(len(chat))} 件")

        # コメントのうち /emotion や /nicoad などの運営コメントを弾く
        # if not re.match … の部分を if re.match … にすると運営コメントだけ取り出せる
        # 全てのコメントを保存する方向にしたのでコメントアウト
        # 参考: https://note.nkmk.me/python-list-clear-pop-remove-del/
        # print(f"/emotion や /nicoad などの運営コメントを除外しています…")
        # chat = [chatitem for chatitem in chat if not re.match(r'/[a-z]+ ', chatitem['chat']['content'])]

        # コメントのうち指定された日付以外に投稿されているものを弾く
        # コメントの投稿時間の日付と、指定された日付が一致するコメントのみ残す
        # 参考: https://note.nkmk.me/python-list-clear-pop-remove-del/
        print(f"{self.date.strftime('%Y/%m/%d')} 以外に投稿されたコメントを除外しています…")
        chat = [chatitem for chatitem in chat if datetime.fromtimestamp(chatitem['chat']['date']).strftime('%Y/%m/%d') == self.date.strftime('%Y/%m/%d')]

        print(f"最終コメント数: {str(len(chat))} 件")

        # xml の場合
        if objformat == 'xml':

            # xml オブジェクトに変換したコメントを返す
            return self.__convertToXML(chat)

        # json の場合
        elif objformat == 'json':

            # 取得したコメントをそのまま返す
            return chat

    # 実況 ID リストを取得
    @staticmethod
    def getJikkyoChannelList():
        return JKComment.jikkyo_channel_table.keys()

    # 実況チャンネル名を取得
    @staticmethod
    def getJikkyoChannelName(jikkyo_id):
        if jikkyo_id in JKComment.jikkyo_channel_table:
            return JKComment.jikkyo_channel_table[jikkyo_id]['name']
        else:
            return None

    # ニコ生がメンテナンス中やサーバーエラーでないかを確認
    @staticmethod
    def getNicoLiveStatus():
        nicolive_url = 'https://live.nicovideo.jp/'
        response = requests.get(nicolive_url, headers={'User-Agent': JKComment.user_agent})
        # HTTP ステータスコードで判定
        if response.status_code == 200:
            return [True, response.status_code]
        else:
            return [False, response.status_code]

    # ニコニコにログインする
    def __login(self, force=False):

        cookie_dump = os.path.dirname(os.path.abspath(sys.argv[0])) + '/cookie.dump'

        # ログイン済み & 強制ログインでないなら以前取得した Cookieを再利用
        if os.path.exists(cookie_dump) and force is False:

            with open(cookie_dump, 'rb') as f:
                cookies = pickle.load(f)
                return cookies.get('user_session')

        else:

            # ログインを実行
            url = 'https://account.nicovideo.jp/api/v1/login'
            post = {'mail': self.nicologin_mail, 'password': self.nicologin_password}
            session = requests.session()
            session.post(url, post, headers={'User-Agent': JKComment.user_agent})

            # Cookie を保存
            with open(cookie_dump, 'wb') as f:
                pickle.dump(session.cookies, f)

            return session.cookies.get('user_session')

    # 視聴セッションへの接続情報を取得
    def __getWatchSessionInfo(self, live_id):

        # 予めログインしておく
        user_session = self.__login()

        def get(user_session):

            # 番組 ID から HTML を取得
            url = 'https://live2.nicovideo.jp/watch/' + live_id
            cookie = {'user_session': user_session}
            response = requests.get(url, cookies=cookie, headers={'User-Agent': JKComment.user_agent})

            if response.status_code != 200:
                raise ResponseError(f'視聴ページの取得に失敗しました。(HTTP Error {response.status_code})')

            # JSON データ (embedded-data) を取得
            soup = BeautifulSoup(response.content, 'html.parser')

            if len(soup.select('script#embedded-data')) == 0:
                raise ResponseError('視聴ページからの embedded-data の取得に失敗しました。メンテナンス中かもしれません。')

            json_raw = soup.select('script#embedded-data')[0].get('data-props', None)
            if json_raw is None:
                raise ResponseError('視聴ページからの embedded-data.data-props の取得に失敗しました。メンテナンス中かもしれません。')
            if type(json_raw) is list:
                json_raw = json_raw[0]

            return json.loads(json_raw)

        # 情報を取得
        watchsession_info = get(user_session)

        # ログインしていなかったらもう一度ログイン
        if watchsession_info['user']['isLoggedIn'] is False:

            # 再ログイン
            user_session = self.__login(True)

            # もう一度情報を取得
            watchsession_info = get(user_session)

        # もう一度ログインしたのに非ログイン状態なら raise
        if watchsession_info['user']['isLoggedIn'] is False:
            raise LoginError('ログインに失敗しました。メールアドレスまたはパスワードが間違っている可能性があります。')

        return watchsession_info

    # コメントセッションへの接続情報を取得
    def __getCommentSessionInfo(self, watchsession_info):

        if ('webSocketUrl' not in watchsession_info['site']['relive'] or watchsession_info['site']['relive']['webSocketUrl'] == ''):
            raise SessionError(
                'コメントセッションへの接続用 WebSocket の取得に失敗しました。\n'
                '一般会員でかつ事前にタイムシフトを予約していなかったか、\n'
                '既にタイムシフト公開期間が終了している可能性があります。'
            )

        # User-Agent は標準のだと弾かれる
        try:
            watchsession = websocket.create_connection(watchsession_info['site']['relive']['webSocketUrl'], timeout=15, header={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36',
                'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits',
                'Sec-WebSocket-Version': '13',
            })
        except ConnectionResetError as ex1:
            raise WebSocketError(f"視聴セッションへの接続がリセットされました。({ex1})")
        except websocket.WebSocketConnectionClosedException as ex2:
            raise WebSocketError(f"視聴セッションへの接続が閉じられました。({ex2})")
        except websocket.WebSocketTimeoutException as ex3:
            raise WebSocketError(f"視聴セッションへの接続がタイムアウトしました。({ex3})")
        except Exception as ex4:
            print(traceback.format_exc(), file=sys.stderr)
            raise WebSocketError(f"視聴セッションへの接続に失敗しました。({ex4})")

        # 視聴セッションリクエストを送る
        watchsession.send(json.dumps({
            'type': 'startWatching',
            'data': {
                'stream': {
                    'quality': 'super_high',
                    'protocol': 'hls',
                    'latency': 'low',
                    'chasePlay': False,
                },
                'room': {
                    'protocol': 'webSocket',
                    'commentable': True,
                },
                'reconnect': False,
            },
        }))

        while True:

            # 受信データを取得
            response_raw = 'Unknown'
            try:
                response_raw = watchsession.recv()
                response = json.loads(response_raw)
            # JSON デコードに失敗
            except json.decoder.JSONDecodeError:
                raise WebSocketError(f"受信データ '{response_raw}' を JSON としてデコードできません。")
            except Exception as ex:
                print(traceback.format_exc(), file=sys.stderr)
                raise WebSocketError(f"視聴セッションからの受信中に予期せぬエラーが発生しました。({ex})")

            # 部屋情報
            if response['type'] == 'room':

                # 視聴セッションを閉じる
                watchsession.close()

                # 部屋情報を返す
                return response['data']

    # スクリーンネームの実況 ID から、実際のニコニコチャンネル/コミュニティの ID と種別を取得する
    def __getRealNicoJikkyoID(self, jikkyo_id):
        if jikkyo_id in JKComment.jikkyo_channel_table:
            return JKComment.jikkyo_channel_table[jikkyo_id]
        else:
            return None

    #  ニコニコチャンネル/コミュニティの ID から、指定された日付に放送されたニコ生の番組 ID を取得する
    def __getNicoLiveID(self, jikkyo_id, date):

        # 実際のニコニコチャンネル/コミュニティの ID と種別を取得
        jikkyo_data = self.__getRealNicoJikkyoID(jikkyo_id)
        if jikkyo_data is None:
            raise JikkyoIDError('指定された実況 ID は存在しません。')

        live_program_infos: list[dict[str, Any]] = []
        live_ids: list[str] = []

        # ニコニコチャンネルのみ
        if jikkyo_data['type'] == 'channel':

            # 放送中番組の ID を取得
            ## 実際にリクエストされる URL: https://live2.nicovideo.jp/watch/ch2646436 (番組 ID の代わりにチャンネル ID を指定)
            watchsession_info = self.__getWatchSessionInfo(jikkyo_data['id'])
            live_ids.append(watchsession_info['program']['nicoliveProgramId'])

            # 過去番組の ID をスクレイピングで取得
            api_url = f'https://sp.ch.nicovideo.jp/api/past_lives/?page=1&channel_id={jikkyo_data["id"]}'
            api_response = requests.get(api_url, headers={'User-Agent': JKComment.user_agent})
            if api_response.status_code != 200:
                raise Exception(f'sp.ch.nicovideo.jp へのリクエストに失敗しました。(HTTP Error {api_response.status_code})')
            soup = BeautifulSoup(api_response.content, 'html.parser')
            for a_tag in soup.find_all('a', href=True):
                href = a_tag['href']
                if 'https://live.nicovideo.jp/watch/' in href:
                    live_ids.append(href.split('/')[-1])

        # ニコニコミュニティのみ
        elif jikkyo_data['type'] == 'community':

            # API にアクセス
            api_url = f"https://com.nicovideo.jp/api/v1/communities/{jikkyo_data['id'][2:]}/lives.json"
            api_response = requests.get(api_url, headers={'User-Agent': JKComment.user_agent})
            if api_response.status_code != 200:
                raise ResponseError(f'com.nicovideo.jp への API リクエストに失敗しました。(HTTP Error {api_response.status_code})')

            api_response_json = json.loads(api_response.content)  # ch とか co を削ぎ落としてから
            if 'data' not in api_response_json:
                raise ResponseError('com.nicovideo.jp への API リクエストに失敗しました。メンテナンス中かもしれません。')

            # 放送 ID を抽出
            for live in api_response_json['data']['lives']:
                # ON_AIR 状態またはタイムシフトが取得可能であれば追加
                # タイムシフトが取得不可のものも含めてしまうと無駄な API アクセスが発生するため
                # live['timeshift']['enabled'] が False の場合、live['timeshift']['can_view'] は要素ごと存在しない
                if (live['status'] == 'ON_AIR' or (live['timeshift']['enabled'] is True and live['timeshift']['can_view'] is True)):
                    live_ids.append(live['id'])

        for live_id in live_ids:

            # API にアクセス
            api_url = f"https://api.cas.nicovideo.jp/v1/services/live/programs/{live_id}"
            api_response = requests.get(api_url, headers={'User-Agent': JKComment.user_agent})
            if api_response.status_code != 200:
                raise ResponseError(f'api.cas.nicovideo.jp への API リクエストに失敗しました。(HTTP Error {api_response.status_code})')

            api_response_json = json.loads(api_response.content)
            if ('data' not in api_response_json) or ('id' not in api_response_json['data']):
                raise ResponseError('api.cas.nicovideo.jp への API リクエストに失敗しました。メンテナンス中かもしれません。')

            # なぜかこの API は ID が文字列なので、互換にするために数値に変換
            api_response_json['data']['id'] = int(api_response_json['data']['id'].replace('lv', ''))

            # live_program_infos にレスポンスデータを入れる
            live_program_infos.append(api_response_json['data'])

        # 開始時刻昇順でソート
        live_program_infos = sorted(live_program_infos, key=lambda x: x['showTime']['beginAt'])

        result: list[str] = []

        for live_program_info in live_program_infos:

            # ISO8601 フォーマットを datetime に変換しておく
            beginAt = datetime.fromisoformat(live_program_info['showTime']['beginAt'])
            endAt = datetime.fromisoformat(live_program_info['showTime']['endAt'])

            # beginAt または endAt の日付と date の日付が一致するなら
            if (beginAt.strftime('%Y/%m/%d') == date.strftime('%Y/%m/%d') or endAt.strftime('%Y/%m/%d') == date.strftime('%Y/%m/%d')):

                # beginAt が現在時刻より後のものを弾く（取得できないので）
                if beginAt < datetime.now().astimezone():

                    # 番組 ID を返す
                    result.append('lv' + str(live_program_info['id']))

        # 取得終了時刻が現在時刻より後（未来）の場合、当然ながら全部取得できないので注意を出す
        # 取得終了が 2020-12-20 23:59:59 で 現在時刻が 2020-12-20 15:00:00 みたいな場合
        # astimezone() しないと比較できない👈重要
        date_235959 = (date + timedelta(hours=23, minutes=59, seconds=59)).astimezone()
        if date_235959 > datetime.now().astimezone():

            print('-' * shutil.get_terminal_size().columns)  # 行区切り
            print(f"注意: {date.strftime('%Y/%m/%d')} 中の放送が終わっていない番組があります。")
            print('現時点で取得できるコメントのみ取得を試みますが、現在時刻までの不完全なログになります。')
            print(f"{date.strftime('%Y/%m/%d')} 中の放送が終わった後に再取得することを推奨します。")

        # 全部回しても取得できなかったら None
        if len(result) == 0:
            return None
        else:
            return result

    # JSON オブジェクトの過去ログを XML オブジェクトの過去ログに変換
    def __convertToXML(self, comments):

        # XML のエレメントツリー
        elemtree = ET.Element('packet')

        # コメントごとに
        for comment in comments:

            # chat 要素を取得
            chat = comment.get('chat')
            if not chat:
                raise ValueError(comment.keys())

            # コメント本文を取得して消す（ XML ではタグ内の値として入るため）
            chat_content = chat.get('content')
            chat.pop('content', '')

            # 属性を XML エレメント内の値として取得
            chat_elemtree = ET.SubElement(elemtree, 'chat', {key: str(value) for key, value in chat.items()})

            # XML エレメント内の値に以前取得した本文を指定
            chat_elemtree.text = chat_content

        return elemtree


# 例外定義
class FormatError(Exception):
    pass
class JikkyoIDError(Exception):
    pass
class LiveIDError(Exception):
    pass
class LoginError(Exception):
    pass
class SessionError(Exception):
    pass
class ResponseError(Exception):
    pass
class WebSocketError(Exception):
    pass
