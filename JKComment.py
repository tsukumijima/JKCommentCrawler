
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import json
import lxml.etree as ET
import os
import pickle
from pprint import pprint
import re
import requests
import websocket


class JKComment:

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
            print(f"コメントを {watchsession_info['program']['title']} から取得します")

            # コメントセッションへの接続情報を取得
            commentsession_info = self.__getCommentSessionInfo(watchsession_info)

            # 取得を開始する時間
            when = endtime

            # Sec-WebSocket-Protocol が重要
            commentsession = websocket.create_connection(commentsession_info['messageServer']['uri'], header={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
                'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits',
                'Sec-WebSocket-Protocol': 'msg.nicovideo.jp#json',
                'Sec-WebSocket-Version': '13',
            })
            
            # コメント情報を入れるリスト
            chat = []

            while True:

                # コメントリクエストを送る
                commentsession.send(json.dumps([
                    { 'ping': {'content': 'rs:0'} },
                    { 'ping': {'content': 'ps:0'} },
                    { 'ping': {'content': 'pf:0'} },
                    { 'ping': {'content': 'rf:0'} },
                    {
                        'thread':{
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

                    # 受信データを取得
                    response = json.loads(commentsession.recv())

                    # スレッド情報
                    if 'thread' in response:

                        # 最後のコメ番
                        last_res = response['thread']['last_res']
                        
                    # コメント情報
                    if 'chat' in response:

                        # /nicoad など特殊コメントは追加せずに次のループへ
                        if re.match(r'/[a-z]+ ', response['chat']['content']):
                            continue

                        # コメントを追加
                        chat_child.append(response)

                        # 最後のコメ番なら while ループを抜ける
                        if last_res == response['chat']['no']:
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
                        chat_child.pop(-1)

                        # 最後のコメ番を更新
                        last_comeban = chat_child[-1]['chat']['no']


                # chat に chat_child の内容を取得
                # 最後のコメントから遡るので、さっき取得したコメントは既に取得したコメントよりも前に連結する
                chat = chat_child + chat
                
                print(str(len(chat)) + '件のコメントを取得しました')

                # コメ番が 1 ならすべてのコメントを取得したと判断して抜ける
                if int(chat[0]['chat']['no']) == 1:
                    break

            print('コメント数: ' + str(len(chat)))
            print(f"コメントを {watchsession_info['program']['title']} から取得しました")

            # 番組単体で取得したコメントを返す
            return chat


        # フォーマット
        objformat = objformat.lower()
        if objformat != 'xml' and objformat != 'json':
            raise Exception('不正なフォーマットです。')

        # 放送 ID らを取得
        # 指定された日付内に放送された全ての番組からコメントを取得するので複数入ることがある
        live_ids = self.__getNicoLiveID(self.jikkyo_id, self.date)
        if live_ids is None:
            raise Exception('放送 ID を取得できませんでした。')

        # コメントを取得
        chat = []
        for live_id in live_ids:
            chat = chat + getCommentOne(live_id)

        # コメントのうち指定された日付以外に投稿されているものを弾く
        # コメントの投稿時間の日付と、指定された日付が一致するコメントのみ残す
        # 参考: https://note.nkmk.me/python-list-clear-pop-remove-del/
        print('合計コメント数: ' + str(len(chat)))
        print('指定された日付以外のコメントを除外しています…')
        chat = [chatitem for chatitem in chat if datetime.fromtimestamp(chatitem['chat']['date']).strftime('%Y-%m-%d') == self.date.strftime('%Y-%m-%d')]

        print('最終コメント数: ' + str(len(chat)))

        # xml の場合
        if objformat == 'xml':

            # xml オブジェクトに変換したコメントを返す
            return self.__convertToXML(chat)

        # json の場合
        elif objformat == 'json':

            # 取得したコメントをそのまま返す
            return chat


    # ニコニコにログインする
    def __login(self, force = False):

        # ログイン済み & 強制ログインでないなら以前取得した Cookieを再利用
        if os.path.exists('cookie.dump') and force == False:

            with open('cookie.dump', 'rb') as f:
                cookies = pickle.load(f)
                return cookies.get('user_session')

        else:

            # ログインを実行
            url = 'https://account.nicovideo.jp/api/v1/login'
            post = { 'mail': self.nicologin_mail, 'password': self.nicologin_password }
            session = requests.session()
            session.post(url, post)

            # Cookie を保存
            with open('cookie.dump', 'wb') as f:
                pickle.dump(session.cookies, f)
            
            return session.cookies.get('user_session')


    # 視聴セッションへの接続情報を取得
    def __getWatchSessionInfo(self, live_id):

        # 予めログインしておく
        user_session = self.__login()

        def get(user_session):

            # 放送 ID から HTML を取得
            url = 'https://live2.nicovideo.jp/watch/' + live_id
            cookie = { 'user_session': user_session }
            response = requests.get(url, cookies=cookie).content

            # JSON データ (embedded-data) を取得
            soup = BeautifulSoup(response, 'html.parser')
            return json.loads(soup.select('script#embedded-data')[0].get('data-props'))

        # 情報を取得
        watchsession_info = get(user_session)

        # ログインしていなかったらもう一度ログイン
        if watchsession_info['user']['isLoggedIn'] == False:

            # 再ログイン
            user_session = self.__login(True)

            # もう一度情報を取得
            watchsession_info = get(user_session)
            
        # もう一度ログインしたのに非ログイン状態なら raise
        if watchsession_info['user']['isLoggedIn'] == False:
            raise Exception('ログインに失敗しました。メールアドレスまたはパスワードが間違っている可能性があります。')

        return watchsession_info


    # コメントセッションへの接続情報を取得
    def __getCommentSessionInfo(self, watchsession_info):

        # User-Agent は標準のだと弾かれる
        watchsession = websocket.create_connection(watchsession_info['site']['relive']['webSocketUrl'], header={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
            'Sec-WebSocket-Extensions': 'permessage-deflate; client_max_window_bits',
            'Sec-WebSocket-Version': '13',
        })

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
            response = json.loads(watchsession.recv())

            # 部屋情報
            if response['type'] == 'room':

                # 視聴セッションを閉じる
                watchsession.close()

                # 部屋情報を返す
                return response['data']


    # スクリーンネームの実況 ID から、実際のニコニコチャンネル/コミュニティの ID と種別を取得する
    def __getRealNicoJikkyoID(self, jikkyo_id):

        table = {
            'jk1':   {'type': 'channel', 'id': 'ch2646436'},
            'jk2':   {'type': 'channel', 'id': 'ch2646437'},
            'jk4':   {'type': 'channel', 'id': 'ch2646438'},
            'jk5':   {'type': 'channel', 'id': 'ch2646439'},
            'jk6':   {'type': 'channel', 'id': 'ch2646440'},
            'jk7':   {'type': 'channel', 'id': 'ch2646441'},
            'jk8':   {'type': 'channel', 'id': 'ch2646442'},
            'jk9':   {'type': 'channel', 'id': 'ch2646485'},
            'jk211': {'type': 'channel', 'id': 'ch2646846'},
        }

        if jikkyo_id in table:
            return table[jikkyo_id]
        else:
            return None


    #  ニコニコチャンネル/コミュニティの ID から、指定された日付に放送されたニコ生の放送 ID を取得する
    def __getNicoLiveID(self, jikkyo_id, date):

        # 実際のニコニコチャンネル/コミュニティの ID と種別を取得
        jikkyo_data = self.__getRealNicoJikkyoID(jikkyo_id)
        if jikkyo_data is None:
            raise Exception('指定された実況 ID は存在しません。')

        # ニコニコチャンネルのみ
        if jikkyo_data['type'] == 'channel':

            # API にアクセス
            api_baseurl = 'https://public.api.nicovideo.jp/v1/channel/channelapp/content/lives.json?sort=startedAt&page=1&channelId='
            api_response = json.loads(requests.get(api_baseurl + jikkyo_data['id'][2:]).content)  # ch とか co を削ぎ落としてから

            # アイテムをソート
            # 参考: https://note.nkmk.me/python-dict-list-sort/
            items = api_response['data']['items']
            items = sorted(items, key=lambda x: x['beginAt'])  # 開始時刻昇順でソート

            result = []

            for item in items:

                # ISO8601 フォーマットを datetime に変換してからフォーマット
                beginAt = datetime.fromisoformat(item['beginAt']).strftime('%Y-%m-%d')
                endAt = datetime.fromisoformat(item['endAt']).strftime('%Y-%m-%d')

                # beginAt または endAt の日付と date の日付が一致するなら
                if beginAt == date.strftime('%Y-%m-%d') or endAt == date.strftime('%Y-%m-%d'):

                    # 放送 ID を返す
                    result.append('lv' + str(item['id']))

            # 全部回しても取得できなかったら None
            if len(result) == 0:
                return None
            else:
                return result

        # ニコニコミュニティのみ
        elif jikkyo_data['type'] == 'community':

            # TODO: ここ書く
            return None


    # JSON オブジェクトの過去ログを XML 形式の過去ログに変換
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
            chat_elemtree = ET.SubElement(elemtree, 'chat', { key: str(value) for key, value in chat.items() })

            # XML エレメント内の値に以前取得した本文指定
            chat_elemtree.text = chat_content

        return elemtree
