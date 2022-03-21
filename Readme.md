
# JKCommentCrawler

![Screenshot](https://user-images.githubusercontent.com/39271166/102918400-2d5bb700-44ca-11eb-8b43-7d5744de8746.png)

ニコ生に移行した新ニコニコ実況の過去ログを日付ごとに一括で取得・保存するツールです。  
Nekopanda 氏が公開されている、旧ニコニコ実況の過去ログデータ一式と互換性のあるファイル・フォルダ構造で保存します。

公式チャンネル ( jk1・jk2・jk4・jk5・jk6・jk7・jk8・jk9・jk101・jk211 ) の放送に加えて、公式では廃止され、現在は [有志のコミュニティ](https://com.nicovideo.jp/community/co5117214) から放送されている NHK BS1・BS11 以外の BS・CS 各局 ( jk103・jk141・jk151・jk161・jk171・jk181・jk191・jk192・jk193・jk222・jk236・jk252・jk260・jk263・jk265・jk333 ) 、地デジ独立局 ( jk10・jk11・jk12 ) の過去ログも収集しています。

## 注意

- このツールは 3 週間で消えてしまう新ニコニコ実況の過去ログを一括で収集するために作られたものです。  
   - [JKCommentGetter](https://github.com/ACUVE/JKCommentGetter) のように時刻を細かく指定して保存するような高度な機能はありません。
- このツールの利用には基本的にニコニコのプレミアムアカウントが必要です。  
  - プレミアムアカウントがなくても事前にタイムシフトを予約しておいた番組であれば取得が可能です。
  - ただし、一般会員ではタイムシフトの同時予約数が 10 に制限されているため、（複垢でも使わない限りは）少なくとも全てのチャンネルの過去ログを取得することはできず、利用に堪えないと思います。
- Nekopanda 氏の過去ログデータ一式と互換性を持たせるため、コメントは番組（スレッド）ごとではなく、日付ごとに保存されます。
  - コミュニティからの放送など同じ日に 3 回放送があるような場合も、同じ日付であれば同じファイルに保存します。
- ini 内のログイン情報を変更したときは、cookie.dump を一旦削除してから JKCommentCrawler を実行してください。
  - cookie.dump は Cookie を保存しているファイルで、このファイルがあるとセッションが切れるまで再ログインを行いません。

## インストール

GitHub の画面内にある緑色の［Code］ボタンをクリックすると［Download Zip］ボタンが表示されるので、ボタンをクリックしてダウンロードします。  
ダウンロードできたら解凍し、適当なフォルダに配置します。

### 設定

JKCommentCrawler を使う前には設定が必要です。まずは JKCommentCrawler.example.ini を JKCommentCrawler.ini にコピーしましょう。

その後、JKCommentCrawler.ini を編集します。  
編集箇所は 過去ログを保存するフォルダ・ニコニコにログインするメールアドレス・ニコニコにログインするパスワード の 3 つです。

過去ログを保存するフォルダは標準では ./kakolog/ になっていますが、これだと JKCommentCrawler を実行したカレントディレクトリによってパスが変わってしまいます。  
できるだけ絶対パスで指定することを推奨します。  
ニコニコにログインするメールアドレス / パスワードも指定します。前述の通り、基本的にプレミアムアカウントのログイン情報が必要です。

これで設定は完了です。

### 実行方法

JKCommentCrawler は Python スクリプトですが、わざわざ環境をセットアップするのも少し手間かなと思ったので、単一の実行ファイルにまとめたものも同梱しています。  
JKCommentCrawler.exe は Windows 用、拡張子なしの JKCommentCrawler は Linux 用の実行ファイルです。  
こちらのバイナリを使ったほうが手軽ですが、一方で特に Windows の場合、Python から普通に実行するときと比べ起動に数秒時間がかかるというデメリットもあります。  
このほか Linux 環境では、ツールを実行する前に `chmod` で JKCommentCrawler ファイルに実行許可を付与しておく必要があるかもしれません。

Python から普通に実行する場合は、別途依存ライブラリのインストールが必要です。  
`pip install -r requirements.txt` ( pip が Python2 の事を指すシステムの場合は pip3 ) と実行し、依存ライブラリをインストールします。  
Python 3.9 で検証しています。Python 2 系は論外として、3.9 未満のバージョンでは動かないかもしれません。

build.sh を実行すればバイナリを自ビルドできますが、PyInstaller と依存ライブラリ諸々が Windows と WSL 側両方に入っている事が前提のため、他の環境でビルドできるかは微妙です。

## 使い方

基本の使い方は以下のようになります。  
ここでは exe 版を使っているものとして説明します。他の実行方法でも拡張子が変わったりなかったりするだけで使い方は同じです。

```
./JKCommentCrawler.exe jk1 2020/12/16
```

`jk1` には実況チャンネル（もし BS11 なら `jk211` ）が、`2020/12/16` には取得したい日の日付が入ります。

前述の通り、コメントは日付単位で保存されます。  
また、/emotion や /nicoad などの運営コメントは公式プレイヤー以外では再現できず、邪魔になりそうなので削除しています。

```
./JKCommentCrawler.exe all 2020/12/16
```

のように、実況チャンネルの代わりに `all` を指定することもできます。

`all` を指定すると、公式チャンネル・コミュニティ全てのチャンネルの過去ログを一括で取得します。  
つまり、この例の場合は 2020 年 12 月 16 日内に放送された（開始時間・終了時間の片方だけ掛かっている場合も含む）、  
`jk1` ～ `jk222` までの全てのチャンネルの番組の過去ログを取得し、  そのうち 2020 年 12 月 16 日中のコメントのみを抽出して実況チャンネルごとに保存します。

大方不具合は直したつもりですが、もし不具合を見つけられた場合は [Issues](https://github.com/tsukumijima/JKCommentCrawler/issues) までお願いします。

## License
[MIT License](LICENSE.txt)