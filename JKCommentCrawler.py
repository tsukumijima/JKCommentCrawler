#! /usr/bin/python3

import argparse
import configparser
import dateutil.parser
import json
import lxml.etree as ET
import os
from pprint import pprint
import shutil
import sys
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
        
        # コメントデータ（XML）を取得
        try:
            comment_xmlobject = jkcomment.getComment(objformat='xml')
        # 処理中断、次のチャンネルに進む
        except JKComment.LiveIDError as ex:
            print(f"{date.strftime('%Y/%m/%d')} 中に放送された番組が見つかりませんでした。")
            print('=' * shutil.get_terminal_size().columns)
            return
        except JKComment.SessionError as ex:
            print(f"エラー: {ex.args[0]}")
            print('=' * shutil.get_terminal_size().columns)
            return

        # XML をフォーマットする
        # lxml.etree を使うことで属性の順序を保持できる
        # 参考: https://banatech.net/blog/view/19
        def prettify(elem):
            # xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
            xml = ET.tostring(elem, encoding='UTF-8', pretty_print=True).decode('UTF-8').replace('>\n  ', '>\n')  # インデントを除去
            xml = xml.replace('<packet>\n', '').replace('</packet>', '').replace('<packet/>', '')
            return xml.rstrip()

        # ファイル名・フォルダ
        os.makedirs(f"{jkcomment_folder}/{jikkyo_id}/{date.strftime('%Y')}/", exist_ok=True)
        filename = f"{jkcomment_folder}/{jikkyo_id}/{date.strftime('%Y')}/{date.strftime('%Y%m%d')}.nicojk"

        # コメントデータ（XML）を保存
        comment_xml = prettify(comment_xmlobject)
        if comment_xml == '':
            print(f"{date.strftime('%Y/%m/%d')} 中のコメントが 0 件のため、ログの保存をスキップします。")
        else:
            with open(filename, 'w') as f:
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
