#!/bin/bash

# WSL で作業していて、かつ Windows 側にも Python の環境があり、
# さらに requirements.txt 内のライブラリが全て入っていることが条件

# Windows 版バイナリをビルド
pwsh.exe -Command pyinstaller JKCommentCrawler.py --onefile --exclude-module numpy --exclude-module pandas
mv dist/JKCommentCrawler.exe JKCommentCrawler.exe
chmod a+x JKCommentCrawler.exe

# Linux 版バイナリをビルド
pyinstaller JKCommentCrawler.py --onefile --exclude-module numpy --exclude-module pandas
mv dist/JKCommentCrawler JKCommentCrawler
chmod a+x JKCommentCrawler
