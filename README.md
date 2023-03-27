# chatbot sample

English | [日本語](./README.ja-JP.md)

Sample for building a self-hosted chatbot  
You can import source code and document files stored on your local PC.

The article [ChatGPT Chatbot for Internal Use](https://zenn.dev/tatsui/articles/langchain-chatbot) introduces the mechanism.

## Demo
![](./docs/img/intelx-demo.gif)

## Frequently Asked Questions.
* Data usage policy
  * Data sent by customers via API Data sent by customers are not used for training in principle (opt-in if you are willing to share data for training).
  * Retain API data for 30 days to monitor for abuse or misuse (after that, delete it. (After that, it will be deleted, except where required by law)
  * A limited number of authorized OpenAI employees and specialized third-party contractors may access this data only to investigate and verify suspected abuse.
  * "Content (input prompts and their responses, uploaded and generated images) in non-API consumer services such as ChatGPT and DALL-E may be used to improve the service
  * Enterprise customers deploying use cases with low potential for abuse could request that no API data be stored at all
* Difference between ChatGPT and ChatGPT API
  * The ChatGPT API is an easier-to-use version of ChatGPT's functionality, allowing programmers to easily use ChatGPT.
  * This sample uses ChatGPT API.
  * To use ChatGPT API, you need to create an OpenAI account and issue an API key.

## Installation
## Set up API key
```bash
export OPENAI_API_KEY=<Open AI API Key>
```

If you need Google search, refer to [Try LangChain's Google custom search integration](https://note.com/npaka/n/nd9a4a26a8932) and set the following.
````bash
export GOOGLE_CSE_ID=
export GOOGLE_API_KEY=
````

Build the container
```bash
docker-compose up -d --build chatbot
```

## create vector database
```bash
docker-compose exec chatbot python /app/ingest.py --help
ingest.py [OPTIONS] TARGET
````
TARGET : Specify the path to the file or directory to be processed. (Required field)  
Options include.

* `-o, --output-file TEXT` : specifies the output vector database file name.
* `-l, --loader-cls [text|pdf_miner|pymupdf|pdf|html]` : Specifies the loader class to use. Default is text.
* `-dl, --dir-loader-cls [directory|readthedocs]` : Specifies the loader class for directories. Default is directory.
* `-e, --file-ext TEXT` : Specifies the file extension to process.
* `-cs, --chunk-size INTEGER` : specifies the size of the text chunks. Default is 1000.
* `-co, --chunk-overlap INTEGER` : specifies overlap of text chunks. Default is 200.
* `-d, --dry-run` : do not actually add the document to the vector store.

For example, . /samples/pdf If you want to create a database file by processing all PDF files in the directory .  
The `-d` option allows you to see the number of tokens and fees that will be consumed without building the database.

```bash
docker-compose exec chatbot python /app/ingest.py -e pdf -l pdf_miner -o /data/projectname -d /samples/pdf
load 654 documents
use 338462 token
price 0.0169231 USD
Dry run mode enabled. Exiting without adding documents to vectorstore.
````

## Start ChatBOT
Set the environment variable to the database file you just saved and start the chatbot.  
Connect to the chatbot via a browser to "http://localhost:3000".
````bash
docker-compose up -d
````

## Reference
* https://dev.classmethod.jp/articles/openai-data-usage-policy/
* https://github.com/hwchase17/chat-langchain
* https://github.com/mckaywrigley/chatbot-ui
