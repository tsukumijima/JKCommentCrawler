#!/usr/bin/env python3

import argparse
import configparser
import datetime
import dateutil.parser
import json
import lxml.etree as ET
import os
import shutil
import sys
import time
import traceback
from pathlib import Path

import JKComment

# バージョン情報
__version__ = '1.8.1'

def main():

    # 引数解析
    parser = argparse.ArgumentParser(description='ニコ生に移行した新ニコニコ実況の過去ログを取得し、Nekopanda 氏が公開されている旧ニコニコ実況の過去ログデータ一式と互換性のあるファイル・フォルダ構造で保存するツール', formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('Channel', help='取得する実況チャンネル (ex: jk211)  all を指定すると全チャンネル取得する')
    parser.add_argument('Date', help='取得する日付 (ex: 2020/12/19)')
    parser.add_argument('--save-dataset-structure-json', action='store_true', help='過去ログデータのフォルダ/ファイル構造を示す JSON ファイルを出力する')
    parser.add_argument('-f', '--force', action='store_true', help='以前取得したログの方が文字数が多い場合でも上書きする')
    parser.add_argument('-v', '--version', action='version', help='バージョン情報を表示する', version='JKCommentCrawler version ' + __version__)
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
        print(f"[{datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')}] " +
              f"{date.strftime('%Y/%m/%d')} 中に放送された {JKComment.JKComment.getJikkyoChannelName(jikkyo_id)} のコメントを取得します。")

        # リトライ回数
        retry_maxcount = 3
        retry_count = 1
        while (retry_count <= retry_maxcount):

            # コメントデータ（XML）を取得
            try:
                comment_xmlobject = jkcomment.getComment(objformat='xml')
                break  # ループを抜ける
            # 処理中断、次のチャンネルに進む
            except JKComment.LiveIDError:
                print(f"{date.strftime('%Y/%m/%d')} 中に放送された番組が見つかりませんでした。")
                print('=' * shutil.get_terminal_size().columns)
                return  # この関数を抜ける
            # 処理中断、終了する
            except JKComment.JikkyoIDError:
                print(f"実況チャンネル {jikkyo_id} に該当するニコニコチャンネルまたはコミュニティが見つかりませんでした。")
                print('=' * shutil.get_terminal_size().columns)
                return  # この関数を抜ける
            # 捕捉された例外
            except (JKComment.SessionError, JKComment.ResponseError, JKComment.WebSocketError) as ex1:
                print('/' * shutil.get_terminal_size().columns, file=sys.stderr)
                print(f"エラー発生時刻: {datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')} 実況ID: {jikkyo_id} リトライ回数: {retry_count}", file=sys.stderr)
                print(f"エラー: [{ex1.__class__.__name__}] {ex1.args[0]}", file=sys.stderr)
                print('/' * shutil.get_terminal_size().columns, file=sys.stderr)
            # 捕捉されない例外
            except Exception as ex2:
                print('/' * shutil.get_terminal_size().columns, file=sys.stderr)
                print(f"エラー発生時刻: {datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')} 実況ID: {jikkyo_id} リトライ回数: {retry_count}", file=sys.stderr)
                print(f"捕捉されないエラー: [{ex2.__class__.__name__}] {ex2.args[0]}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                print('/' * shutil.get_terminal_size().columns, file=sys.stderr)

            # リトライカウント
            retry_count = retry_count + 1

            # 3 秒スリープ
            if retry_count <= retry_maxcount:
                time.sleep(3)

        # 3 回リトライしてもうまくいかなかったら終了
        if retry_count >= retry_maxcount:
            print('/' * shutil.get_terminal_size().columns, file=sys.stderr)
            print(f"エラー発生時刻: {datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')} 実況ID: {jikkyo_id} リトライに失敗しました。スキップします。", file=sys.stderr)
            print('/' * shutil.get_terminal_size().columns, file=sys.stderr)
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
        elif filelength > len(comment_xml) and args.force is False:
            print(f'以前取得したログの方が文字数が多いため、ログの保存をスキップします。(以前: {filelength}文字, 今回: {len(comment_xml)}文字)')
        else:
            if filelength > len(comment_xml) and args.force is True:
                print(f'以前取得したログの方が文字数が多いですが、--force が指定されているため、ログを上書き保存します。(以前: {filelength}文字, 今回: {len(comment_xml)}文字)')
            with open(filename, 'w', encoding='UTF-8') as f:
                f.write(comment_xml)
                print(f"ログを {filename} に保存しました。")

        # 行区切り
        print('=' * shutil.get_terminal_size().columns)

    # ニコ生がメンテナンス中やサーバーエラーでないかを確認
    nicolive_status, nicolive_status_code = JKComment.JKComment.getNicoLiveStatus()
    if nicolive_status is False:
        print('/' * shutil.get_terminal_size().columns, file=sys.stderr)
        print(f"エラー発生時刻: {datetime.datetime.now().strftime('%Y/%m/%d %H:%M:%S')}", file=sys.stderr)
        if nicolive_status_code == 500:
            print('エラー: 現在、ニコ生で障害が発生しています。(HTTP Error 500)', file=sys.stderr)
        elif nicolive_status_code == 503:
            print('エラー: 現在、ニコ生はメンテナンス中です。(HTTP Error 503)', file=sys.stderr)
        else:
            print(f"エラー: 現在、ニコ生でエラーが発生しています。(HTTP Error {nicolive_status_code})", file=sys.stderr)
        print('/' * shutil.get_terminal_size().columns, file=sys.stderr)
        print('=' * shutil.get_terminal_size().columns)
        sys.exit(1)

    # コメントデータ（XML）を全てのチャンネル分取得
    if jikkyo_id.lower() == 'all':
        for jikkyo_id_ in JKComment.JKComment.getJikkyoChannelList():
            get(jikkyo_id_, date)

    # コメントデータ（XML）を単一チャンネル分取得
    else:
        get(jikkyo_id, date)

    # --save-dataset-structure-json が指定されている場合
    if args.save_dataset_structure_json is True:
        def get_directory_contents(directory_path: str, nest: bool = False) -> dict[str, dict[str, dict[str | None]]]:
            path = Path(directory_path)
            if not path.exists():
                raise FileNotFoundError(f'Directory "{directory_path}" does not exist.')
            data = {}
            for item in sorted(path.iterdir()):
                if item.is_dir() and (item.name.startswith('jk') or nest is True):
                    data[item.name] = get_directory_contents(item, nest=True)
                elif item.is_file() and nest is True:
                    data[item.name] = None
            return data

        data = get_directory_contents(jkcomment_folder)
        with open(f'{jkcomment_folder}/dataset_structure.json', 'w', encoding='UTF-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print(f'データセットの構造を {jkcomment_folder}/dataset_structure.json に保存しました。')
        print('=' * shutil.get_terminal_size().columns)


if __name__ == '__main__':
    main()
