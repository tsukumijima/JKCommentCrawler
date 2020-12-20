
import dateutil.parser
from pprint import pprint
import lxml.etree as ET
import xml.dom.minidom as minidom
import argparse
import json
import os

import config
from JKComment import JKComment


def main():

    # 引数解析
    parser = argparse.ArgumentParser(description = 'ニコ生に移行した新ニコニコ実況の過去ログを取得し、Nekopanda 氏が公開されている旧ニコニコ実況の過去ログデータ一式と互換性のあるファイル・フォルダ構造で保存するツール', formatter_class = argparse.RawTextHelpFormatter)
    parser.add_argument('Channel', help = '取得する実況チャンネル (ex: jk211)')
    parser.add_argument('Date', help = '取得する日付 (ex: 2020-12-19)')
    args = parser.parse_args()

    # 引数
    jikkyo_id = args.Channel.rstrip()
    date = dateutil.parser.parse(args.Date.rstrip())

    # インスタンスを作成
    jkcomment = JKComment(jikkyo_id, date, config.nicologin_mail, config.nicologin_password)

    # コメントデータ（XML）を取得
    comment_xmlobject = jkcomment.getComment(objformat='xml')

    # XML をフォーマットする
    # lxml.etree を使うことで属性の順序を保持できる
    # 参考: https://banatech.net/blog/view/19
    def prettify(elem):
        # xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml = ET.tostring(elem, encoding='UTF-8', pretty_print=True).decode('UTF-8').replace('>\n  ', '>\n')  # インデントを除去
        xml = xml.replace('<packet>\n', '').replace('</packet>', '')
        return xml.rstrip()

    # ファイル名・フォルダ
    os.makedirs(f'{config.jkcomment_folder}/{jikkyo_id}/{date.strftime("%Y")}/', exist_ok=True)
    filename = f'{config.jkcomment_folder}/{jikkyo_id}/{date.strftime("%Y")}/{date.strftime("%Y%m%d")}.nicojk'

    # コメントデータ（XML）を保存
    with open(filename, 'w') as f:
        f.write(prettify(comment_xmlobject))

    # TODO: コミュニティにも対応する


if __name__ == '__main__':
    main()
