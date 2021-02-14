#!/usr/bin/python3

import argparse
import configparser
import datetime
import dateutil.parser
import json
import lxml.etree as ET
import os
from pprint import pprint
import shutil
import sys
import traceback
import xml.dom.minidom as minidom

import JKComment

# バージョン情報
__version__ = '1.0.0'

def main():

    # 引数解析
    parser = argparse.ArgumentParser(description = 'ニコ生に移行した新ニコニコ実況の過去ログを取得し、Nekopanda 氏が公開されている旧ニコニコ実況の過去ログデータ一式と互換性のあるファイル・フォルダ構造で保存するツール', formatter_class = argparse.RawTextHelpFormatter)
    parser.add_argument('Channel', help = '取得する実況チャンネル (ex: jk211)  all を指定すると全チャンネル取得する')
    parser.add_argument('Date', help = '取得する日付 (ex: 2020-12-19)')
    parser.add_argument('-v', '--version', action='version', help = 'バージョン情報を表示する', version='JKCommentCrawler version ' + __version__)
    args = parser.parse_args()

    # 引数
    jikkyo_id = args.Channel.rstrip()
    date = dateutil.parser.parse(args.Date.rstrip())

    # 設定読み込み
    config_ini = os.path.dirname(os.path.abspath(sys.argv[0])) + '/JKCommentCrawler.ini'
    if not os.path.exists(config_ini):
        raise Exception('JKCommentCrawler.ini が存在しません。JKCommentCrawler.example.ini からコピーし、\n適宜設定を変更して JKCommentCrawler と同じ場所に配置してください。')
    config = configparser.ConfigParser()
    config.read(config_ini, encoding='UTF-8')

    jkcomment_folder = config.get('Default', 'jkcomment_folder').rstrip('/')
    nicologin_mail = config.get('Default', 'nicologin_mail')
    nicologin_password = config.get('Default', 'nicologin_password')

    # 行区切り
    print('=' * shutil.get_terminal_size().columns)


    def get(jikkyo_id, date):

        # インスタンスを作成
        jkcomment = JKComment.JKComment(jikkyo_id, date, nicologin_mail, nicologin_password)
        print(f"{date.strftime('%Y/%m/%d')} 中に放送された {JKComment.JKComment.getJikkyoChannelName(jikkyo_id)} のコメントを取得します。")

        # リトライ回数
        retry_maxcount = 3
        retry_count = 1
        while (retry_count <= retry_maxcount):

            # コメントデータ（XML）を取得
            try:
                comment_xmlobject = jkcomment.getComment(objformat='xml')
                break  # ループを抜ける
            # 処理中断、次のチャンネルに進む
            except JKComment.LiveIDError as ex:
                print(f"{date.strftime('%Y/%m/%d')} 中に放送された番組が見つかりませんでした。")
                print('=' * shutil.get_terminal_size().columns)
                return  # この関数を抜ける
            # 捕捉された例外
            except (JKComment.SessionError, JKComment.ResponseError, JKComment.WebSocketError) as ex:
                print('/' * shutil.get_terminal_size().columns, file=sys.stderr)
                print(f"エラー発生時刻: {datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')} 実況ID: {jikkyo_id} リトライ回数: {retry_count}", file=sys.stderr)
                print(f"エラー: [{ex.__class__.__name__}] {ex.args[0]}", file=sys.stderr)
                print('/' * shutil.get_terminal_size().columns, file=sys.stderr)
            # 捕捉されない例外
            except Exception as ex:
                print('/' * shutil.get_terminal_size().columns, file=sys.stderr)
                print(f"エラー発生時刻: {datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')} 実況ID: {jikkyo_id} リトライ回数: {retry_count}", file=sys.stderr)
                print(f"エラー: [{ex.__class__.__name__}] {ex.args[0]}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                print('/' * shutil.get_terminal_size().columns, file=sys.stderr)

            # リトライカウント
            retry_count = retry_count + 1

        # 3 回リトライしてもうまくいかなかったら終了
        if retry_count >= retry_maxcount:
            print('リトライに失敗しました。スキップします。')
            print('=' * shutil.get_terminal_size().columns)
            return

        # XML をフォーマットする
        # lxml.etree を使うことで属性の順序を保持できる
        # 参考: https://banatech.net/blog/view/19
        def format_xml(elem):
            # xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
            xml = ET.tostring(elem, encoding='UTF-8', pretty_print=True).decode('UTF-8').replace('>\n  ', '>\n')  # インデントを除去
            xml = xml.replace('<packet>\n', '').replace('</packet>', '').replace('<packet/>', '')
            return xml.rstrip()

        # XML にフォーマット
        comment_xml = format_xml(comment_xmlobject)

        # ファイル名・フォルダ
        os.makedirs(f"{jkcomment_folder}/{jikkyo_id}/{date.strftime('%Y')}/", exist_ok=True)
        filename = f"{jkcomment_folder}/{jikkyo_id}/{date.strftime('%Y')}/{date.strftime('%Y%m%d')}.nicojk"

        # 既にファイルが存在していたら文字数を取得
        if os.path.exists(filename):
            with open(filename, 'r', encoding='UTF-8') as f:
                filelength = len(f.read())
        else:
            filelength = 0

        # コメントデータ（XML）を保存
        if comment_xml == '':
            print(f"{date.strftime('%Y/%m/%d')} 中のコメントが 0 件のため、ログの保存をスキップします。")
        # 以前取得したログの方が今取得したログよりも文字数が多いとき
        # タイムシフトの公開期限が終了したなどの理由で以前よりもログ取得が少なくなる場合に上書きしないようにする
        elif filelength > len(comment_xml):
            print('以前取得したログの方が文字数が多いため、ログの保存をスキップします。')
        else:
            with open(filename, 'w', encoding='UTF-8') as f:
                f.write(comment_xml)
                print(f"ログを {filename} に保存しました。")

        # 行区切り
        print('=' * shutil.get_terminal_size().columns)


    # コメントデータ（XML）を全てのチャンネル分取得
    if jikkyo_id.lower() == 'all':
        for jikkyo_id_ in JKComment.JKComment.getJikkyoIDList():
            get(jikkyo_id_, date)

    # コメントデータ（XML）を単一チャンネル分取得
    else:
        get(jikkyo_id, date)


if __name__ == '__main__':
    main()
