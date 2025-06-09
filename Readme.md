
# JKCommentCrawler

![Screenshot](https://github.com/user-attachments/assets/6cbf9bb8-dbd8-473a-a25a-e5f78264bcf4)

**ニコニコ生放送統合後の [ニコニコ実況](https://jk.nicovideo.jp/)・[NX-Jikkyo](https://nx-jikkyo.tsukumijima.net/) の過去ログを日付ごとに一括で収集・保存するツールです。**  
かつて [Nekopanda](https://github.com/nekopanda) 氏が公開されていた、旧ニコニコ実況の過去ログデータ一式と互換性のあるファイル・フォルダ構造で保存します。

> [!WARNING]    
> **JKCommentCrawler v2 では、すべてのコードが全面的に書き直されています。**  
> コマンドライン引数や ini ファイルの構成には互換性がありますが、コンソール表示や実装仕様は大幅に変更されています。  
> **メッセージサーバーの仕様が変更された 2024/08/05 復旧以降のニコニコ生放送上の [ニコニコ実況](https://jk.nicovideo.jp/) に加え、ニコニコ実況が復旧するまでの避難所（現在は主に [ニコニコミュニティの廃止](https://blog.nicovideo.jp/niconews/225559.html) により存続困難になった非公式チャンネル向けの実況用代替コメントサーバー）である [NX-Jikkyo](https://nx-jikkyo.tsukumijima.net/) の両方のコメントを収集できます。**

> [!TIP]
> JKCommentCrawler v2 では、ニコニコ生放送の新メッセージサーバーからのコメント取得処理に、今回新規開発した [NDGRClient](https://github.com/tsukumijima/NDGRClient) を使用しています。  
> ニコニコ実況以外のニコニコ生放送番組のコメントを取得する用途でも使えますので、よろしければご活用ください。

> [!TIP]
> **JKCommentCrawler で5分おきに収集したニコニコ実況・NX-Jikkyo の過去ログは、[Hugging Face (KakologArchives)](https://huggingface.co/datasets/KakologArchives/KakologArchives) に公開しています！**  
> **また Hugging Face に保存された過去ログデータセットをデータソースとして、[ニコニコ実況 過去ログ API](https://jikkyo.tsukumijima.net/) を運営中です。**   
> 
> JKCommentCrawler 自体、元々 [ニコニコ実況 過去ログ API](https://jikkyo.tsukumijima.net/) で配信する過去ログコメントを収集する目的で開発されたものです。  
> 通常は [ニコニコ実況 過去ログ API](https://jikkyo.tsukumijima.net/) からのコメント取得をおすすめします。実況チャンネル・開始日時・終了日時で膨大なコメントを絞り込み、XML または JSON 形式で取得できます。

## 対応実況チャンネル

> [!NOTE]
> `jk` から始まる実況チャンネル ID は、2020/12/14 までの旧ニコニコ実況で使われていた ID 表記を概ね継承しています。  
> 一方 `jk260` や `jk333` など、旧ニコニコ実況では存在しなかったものの、各クライアントでの慣行を継承して「`jk` + チャンネル番号」形式で振られている実況チャンネル ID もあります。

### 地上波

- `jk1` : NHK総合 - [[ニコニコ実況]](https://live.nicovideo.jp/watch/ch2646436) [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk1)
- `jk2` : NHK Eテレ - [[ニコニコ実況]](https://live.nicovideo.jp/watch/ch2646437) [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk2)
- `jk4` : 日本テレビ - [[ニコニコ実況]](https://live.nicovideo.jp/watch/ch2646438) [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk4)
- `jk5` : テレビ朝日 - [[ニコニコ実況]](https://live.nicovideo.jp/watch/ch2646439) [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk5)
- `jk6` : TBSテレビ - [[ニコニコ実況]](https://live.nicovideo.jp/watch/ch2646440) [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk6)
- `jk7` : テレビ東京 - [[ニコニコ実況]](https://live.nicovideo.jp/watch/ch2646441) [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk7)
- `jk8` : フジテレビ - [[ニコニコ実況]](https://live.nicovideo.jp/watch/ch2646442) [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk8)
- `jk9` : TOKYO MX - [[ニコニコ実況]](https://live.nicovideo.jp/watch/ch2646485) [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk9)
- `jk10` : テレ玉 - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk10)
- `jk11` : tvk - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk11)
- `jk12` : チバテレビ - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk12)
- `jk13` : サンテレビ - [[ニコニコ実況]](https://live.nicovideo.jp/watch/ch2649860) [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk13)
- `jk14` : KBS京都 - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk14)

### BS・CS

- `jk101` : NHK BS - [[ニコニコ実況]](https://live.nicovideo.jp/watch/ch2647992) [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk101)
- `jk103` : NHK BSプレミアム - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk103)
- `jk141` : BS日テレ - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk141)
- `jk151` : BS朝日 - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk151)
- `jk161` : BS-TBS - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk161)
- `jk171` : BSテレ東 - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk171)
- `jk181` : BSフジ - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk181)
- `jk191` : WOWOW PRIME - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk191)
- `jk192` : WOWOW LIVE - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk192)
- `jk193` : WOWOW CINEMA - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk193)
- `jk200` : BS10 - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk200)
- `jk201` : BS10スターチャンネル - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk201)
- `jk211` : BS11 - [[ニコニコ実況]](https://live.nicovideo.jp/watch/ch2646846) [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk211)
- `jk222` : BS12 - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk222)
- `jk236` : BSアニマックス - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk236)
- `jk252` : WOWOW PLUS - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk252)
- `jk260` : BS松竹東急 - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk260)
- `jk263` : BSJapanext - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk263)
- `jk265` : BSよしもと - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk265)
- `jk333` : AT-X - [[NX-Jikkyo]](https://nx-jikkyo.tsukumijima.net/watch/jk333)

## いわゆる「コミュニティ実況」と NX-Jikkyo の関係について

**2020/12/15 のニコニコ実況のニコニコ生放送への統合により、tvk などの地上波独立局と、BS11 を除く大半の BS チャンネルの実況チャンネルが「公式には」廃止されてしまいました。**（スポーツ実況で需要が多いからか、2021 年に NHK BS1 のみ復活しています。）  
統合後のニコニコ実況は「チャンネル生放送」扱いのため、24時間365日真っ暗な映像が無駄に 1080p で放送され続けることによる多大な配信コストが、実況チャンネル数縮小の理由だと推測されています。  
しかし、**特に TOKYO MX が映らない地方在住の BS アニメ実況民などから「廃止された実況チャンネルでも実況を続けたい」という要望が根強く出ていました。**   

> [!NOTE]
> 「ニコニコ実況のためにチャンネル生放送に映像・音声なし（せめて音声のみ）で配信できる仕組みを作れば良かったのでは？」という疑問は残りますが、不採算事業であるニコニコ実況のためだけに、複雑怪奇なニコニコ生放送のシステムを改修するコストと手間は掛けられないという経営判断なのでしょう。
   
一方、かつて存在したニコニコミュニティでは「不特定多数のユーザーが、コミュニティに紐づいて生放送番組を放送できる」「コミュニティ内で同時に放送できるのは一人だけ」という、ニコニコ実況的なものを不特定多数のユーザーで協力しながら実現するのに大変都合の良い仕組みが用意されていました。  
さらに旧来のニコニコ実況ページに代わって設置された [ニコニコ実況の新ポータル](https://jk.nicovideo.jp) は「ニコニコ実況」タグがつけられたユーザー生放送番組が、公式実況チャンネルへのリンクの下にランダム表示される仕様となっていました。

**そうした状況を踏まえ、有志らの尽力で公式では廃止された各チャンネルごとに [ニコニコミュニティ](https://web.archive.org/web/20240522154158/https://com.nicovideo.jp/community/co5117214) が開設され、プレミアム会員の有志が「ユーザー生放送」で実況用番組の放送枠を取ることによる、いわゆる「コミュニティ実況」の慣習が自然発生的に成立しました。**

この「コミュニティ実況」はプレミアム会員を辞めて継続できなくなる人が現れるなど何度も存続の危機に陥りつつも、私が開発した [JKLiveReserver](https://github.com/tsukumijima/JKLiveReserver) で自動枠取りできるようになった効果もあり、綱渡りながら長年維持されてきました。

徐々に TVTest ([NicoJK](https://github.com/xtne6f/NicoJK)) などのサードパーティー実況クライアントでも「コミュニティ実況」への対応が進み、事実上のデファクトスタンダートとなっていった経緯があります。

> [!NOTE]
> 技術的にも「コミュニティ実況」方式であれば、サードパーティークライアント側で各チャンネルごとの実況コミュニティの ID をハードコードし、当該コミュニティで放送中の番組を問答無用で「実況用番組枠」とみなせば、各 BS チャンネルに対応する実況用番組のコメントを流せる（＝表面上は公式チャンネルと変わらない UI でコメントを表示・投稿できる）メリットがありました。

> [!NOTE]
> ニコニコ生放送では、実際には OBS などから配信を行わなくても（真っ黒画面ではありますが）放送できる仕様です。他方、一般会員の最大配信時間は 30 分までに制限されています。  
> さらに YouTube Live と異なり、一つのアカウントで同時に配信できる番組は一つまでの制限があります。  
> このため廃止された全実況チャンネルで「コミュニティ実況」を行うには、チャンネル数分のプレミアム会員が連携をとる必要がありました。

しかし、**2024/06/08 のニコニコへの大規模なサイバー攻撃により、ニコニコ生放送/ニコニコ実況にも2ヶ月近くにわたりアクセスできなくなりました。**    
何ヶ月も実況できない時間が続くことで実況過去ログに大きな穴があき、ひいては「ニコニコ実況」という文化自体が壊滅することを危惧した私は、**急遽 [NX-Jikkyo](https://nx-jikkyo.tsukumijima.net/) を開発し、運営を開始しました。**  

> [!NOTE]
**NX-Jikkyo は、ニコニコ生放送の WebSocket API 仕様とのほぼ完全な互換性を持つ、実況用代替コメントサーバーです。**  
ニコニコ生放送向けのコメント受信処理を置き換えるだけで対応できる設計にしたことが奏功し、すぐに各サードパーティークライアントでも対応していただきました。

その後ニコニコ生放送は 2024/08/05 に復旧しましたが、**今まで「コミュニティ実況」で利用されていたニコニコミュニティは復旧が困難として、そのままサービスを終了してしまいました。**

- 元から近年プレミアム会員費の値上げなどで「コミュニティ実況」が存続の危機に瀕していたこと
- 「ニコニコ実況避難所」として jkcommentviewer をはじめとした各種のサードパーティークライアントで対応済みなこと
- ニコニコ生放送復旧までの2ヶ月間実際に使ってみて概ね問題なく、むしろ使いやすいと評する人が多かったこと
- 過去ログデータ取得の事実上のデファクトスタンダードである [ニコニコ実況 過去ログ API](https://jikkyo.tsukumijima.net/) に過去ログが反映され、この API に依存している各クライアントでもニコニコ実況に投稿されたコメント同様に表示できること
- ニコニコ実況公式で用意されている実況チャンネルのコメントもリアルタイム表示できること

上記条件が積み重なった結果、**BS アニメ実況民らによる暗黙の了解として「公式にない民放 BS などの実況チャンネルは引き続き NX-Jikkyo で実況する」流れになりつつあります。**

**JKCommentCrawler v2 ではこうした流れを踏まえ、本家ニコニコ実況と NX-Jikkyo 両方に投稿されたコメントを時系列で統合して保存するようになりました。**  
[ニコニコ実況 過去ログ API](https://jikkyo.tsukumijima.net/) の API レスポンスには引き続き互換性を持たせており、既存クライアントをなるべく改修することなく、ニコニコ実況・NX-Jikkyo 双方のコメントをシームレスに一緒に楽しめる形を目指していきます。

> [!NOTE]
> NX-Jikkyo では、本家ニコニコ実況に投稿されたコメントをリアルタイムにマージし、随時配信しています。  
> しかしリアルタイムマージの性質上完璧なマージは難しく、サーバー再起動などによりコメントを取りこぼしてしまうことも稀にあります。  
> **オリジナルに近い情報量のコメントデータを、可能な限り収集して後世に残していくために、改めて JKCommentCrawler にて双方の過去ログコメントを収集し、時系列に並べ替え統合した上で保存・反映しています。**

## 注意

- **JKCommentCrawler は、3 週間で消えてしまう新ニコニコ実況の過去ログを、一括で自動収集するために開発されました。**  
  - 可能な限りすべての過去ログコメントを継続的に収集するユースケースを前提に設計しており、一部時間の過去ログだけを取得する用途は想定していません。
    - 一部時間の過去ログを抜き出して取得したい方は、代わりに [ニコニコ実況 過去ログ API](https://jikkyo.tsukumijima.net/) を利用してください。
  - [JKCommentGetter](https://github.com/ACUVE/JKCommentGetter) のように、詳細に時刻を指定して保存するなどの高度な機能はありません。
- **JKCommentCrawler を利用するには、基本的にニコニコのプレミアムアカウントが必要です。**  
  - プレミアムアカウントがなくても、事前にタイムシフトを予約しておいた番組であれば過去ログ収集が可能です。
  - ただし、一般会員ではタイムシフトの同時予約数が 10 に制限されています。そのため（複垢でも使わない限りは）全てのチャンネルの過去ログを収集することはできず、利用に堪えないと思います。
- **Nekopanda 氏の過去ログデータ一式と互換性を持たせるため、コメントは番組（スレッド）ごとではなく、日付ごとに保存されます。**
  - 同じ日に放送された実況用番組が複数回あるケースでは、一旦同じ日に放送された実況用番組のコメントをすべてダウンロードした上で、指定された日付以外に投稿されたコメントを除外し、日付ごとのファイルに保存します。
- **JKCommentCrawler.ini に記載されたニコニコアカウントのログイン情報を変更したときは、cookies.json を一旦削除してから再度 JKCommentCrawler を実行してください。**
  - cookies.json は Cookie を保存しているファイルです。このファイルが配置された状態では、ログインセッションが切れるまで再ログインを行いません。

## インストール

事前に Python 3.11 がインストールされている必要があります。

```bash
git clone https://github.com/tsukumijima/JKCommentCrawler.git
cd JKCommentCrawler
pip install poetry
poetry install
```

JKCommentCrawler を使う前には設定が必要です。  
まずは `JKCommentCrawler.example.ini` を `JKCommentCrawler.ini` にコピーしましょう。

その後、`JKCommentCrawler.ini` を編集します。  
編集箇所は「過去ログを保存するフォルダ」「ニコニコアカウントのメールアドレス」「ニコニコアカウントのパスワード」の 3 つです。

```ini
[Default]

# ====================  環境設定  ====================
# JKCommentCrawler.ini にコピーした上で、各自の環境に合わせて編集してください
# メールアドレス・パスワードを変更した時は、cookies.json ファイルを削除してから実行してください

# 過去ログを保存するフォルダ
jkcomment_folder = ./kakolog/

# ニコニコにログインするメールアドレス
nicologin_mail = example@example.com

# ニコニコにログインするパスワード
nicologin_password = example_password
```

過去ログの保存先フォルダは標準では `./kakolog/` になっていますが、これだと JKCommentCrawler を実行したカレントディレクトリによってパスが変わってしまいます。  
念のため、できるだけ絶対パスで指定することを推奨します。

また、ニコニコアカウントのメールアドレス / パスワードも指定します。前述の通り、基本的にプレミアムアカウントのログイン情報が必要です。

> [!IMPORTANT]
> ニコニコアカウントの 2 要素認証 (2FA) には対応していません。  
> お手元のニコニコアカウントで 2FA が有効な場合は、一旦解除してから再度 JKCommentCrawler を実行してください。

これで設定は完了です。

## 使い方

```bash
 Usage: python -m jkcommentcrawler [OPTIONS] CHANNEL_ID DATE

 JKCommentCrawler: Nico Nico Jikkyo Comment Crawler

╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────╮
│ *    channel_id      TEXT  コメントを収集する実況チャンネル。(ex: jk211) all                     │
│                            を指定すると全チャンネルのコメントを収集する。                        │
│                            [default: None]                                                       │
│                            [required]                                                            │
│ *    date            TEXT  コメントを収集する日付。(ex: 2024/08/05) [default: None] [required]   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────╮
│ --save-dataset-structure-json            過去ログデータのフォルダ/ファイル構造を示す JSON        │
│                                          ファイルを出力する。                                    │
│ --force                        -f        以前取得したログの方が文字数が多い場合でも上書きする。  │
│ --verbose                      -v        詳細なログを表示する。                                  │
│ --version                                バージョン情報を表示する。                              │
│ --install-completion                     Install completion for the current shell.               │
│ --show-completion                        Show completion for the current shell, to copy it or    │
│                                          customize the installation.                             │
│ --help                                   Show this message and exit.                             │
╰──────────────────────────────────────────────────────────────────────────────────────────────────╯
```

```bash
poetry run python -m jkcommentcrawler jk1 2024/08/05
```

`jk1` には実況チャンネル ID (ex: BS11 なら `jk211`) が、`2024/08/05` には収集対象の過去ログが投稿された日付が入ります。

各実況チャンネルのコメントは、日付ごとに `./kakolog/jk1/2024/20240805.nicojk` に保存されます。

> [!NOTE]
> .nicojk という拡張子ではありますが、実際はヘッダーなしの XML ファイルです。  
> Nekopanda 氏がかつて公開されていた過去ログデータ一式の拡張子が .nicojk だったため、それに合わせています。

> [!IMPORTANT]
> 従来の JKCommentCrawler v1 では、`/emotion` や `/nicoad` などの運営コメントも保存されていました。  
> しかしメッセージサーバーの仕様が変更された 2024/08/05 復旧以降のニコニコ生放送ではコメント配信形式が Protocol Buffers で構造化された関係で、「運営コメント」という概念自体が廃止されています。  
> その関係で、JKCommentCrawler v2 では運営コメントは保存されなくなっています。

![Screenshot](https://github.com/user-attachments/assets/5dbae17e-4646-4f80-82ca-c3545d0bd46c)

```bash
poetry run python -m jkcommentcrawler all 2024/08/05
```

実況チャンネル ID を指定する代わりに、`all` を指定することもできます。
**`all` を指定すると、指定された日付の全実況チャンネルの過去ログを一括で収集します。**  

> [!TIP]
> この例では、 2024/08/05 内に放送された（開始時間・終了時間の片方だけ 2024/08/05 に掛かっている場合も含む）`jk1` ～ `jk333` までの全実況チャンネルの過去ログを収集し、そのうち 2024/08/05 中のコメントのみを抽出して各実況チャンネルごとに保存します。

大方不具合は直したつもりですが、もし不具合を見つけられた場合は [Issues](https://github.com/tsukumijima/JKCommentCrawler/issues) までお願いします。

## License

[MIT License](License.txt)
