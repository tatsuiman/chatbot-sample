FROM python:3.10

# Tiktoken requires Rust toolchain, so build it in a separate stage
RUN apt-get update && apt-get install -y gcc curl
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y && apt-get install --reinstall libc6-dev -y
ENV PATH="/root/.cargo/bin:${PATH}"

COPY ./requirements.txt .
RUN pip install --upgrade pip
RUN pip3 install -r requirements.txt

COPY ./app /app
COPY ./*.sh /
WORKDIR /app
ENTRYPOINT ["/entrypoint.sh"]
