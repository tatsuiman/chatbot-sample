# chatbot sample

langchainを使ってローカルチャットボットを構築するサンプル  
[chat-langchain](https://github.com/hwchase17/chat-langchain)を参考に作りました。

[ChatGPTで社内用チャットボットを作った話](https://zenn.dev/tatsui/articles/langchain-chatbot)の記事で仕組みを紹介しています。

## インストール
```
pip install -r requirements.txt
```

## APIキーの設定
```
export OPENAI_API_KEY=<Open AI API Key>
```

## ベクトルデータベースの作成
```bash
ingest.py [OPTIONS] TARGET
```
TARGET : 処理するファイルやディレクトリのパスを指定します。(必須項目)  
オプションには以下のものがあります。

* `-o, --output-file TEXT` : 出力ベクトルデータベースファイル名を指定します。
* `-l, --loader-cls [text|pdf_miner|pymupdf|pdf|html]` : 使用するローダークラスを指定します。デフォルトは text です。
* `-dl, --dir-loader-cls [directory|readthedocs]` : ディレクトリ用のローダークラスを指定します。デフォルトは directory です。
* `-e, --file-ext TEXT` : 処理するファイルの拡張子を指定します。
* `-cs, --chunk-size INTEGER` : テキストチャンクのサイズを指定します。デフォルトは 1000 です。
* `-co, --chunk-overlap INTEGER` : テキストチャンクのオーバーラップを指定します。デフォルトは 200 です。
* `-d, --dry-run` : ドキュメントをベクトルストアに実際に追加しない。

例えば、/data ディレクトリにあるすべてのPDFファイルを処理して、データベースファイルを output.pkl に指定する場合は、以下のようにします。  
`-d`オプションをつける事でデータベース構築を行わずに消費されるトークン数と料金を確認することができます。

```bash
python ingest.py -e pdf -l pdf_miner -o output.pkl -d /data
load 654 documents
use 338462 token
price 0.0169231 USD
Dry run mode enabled. Exiting without adding documents to vectorstore.
```

## ChatBOTの起動
```bash
python chat-cli.py -f output.pkl
```

## WebUI
```bash
python webui.py output.pkl
```
