# langchain chatgpt

langchainを使ってローカルチャットボットを構築するサンプル

## ベクトルデータベースの作成
```bash
ingest.py [OPTIONS] TARGET
```
TARGET : 処理するファイルやディレクトリのパスを指定します。必須項目です。
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
