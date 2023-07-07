FROM python:3.10.8-slim-buster AS runner

RUN apt-get update
RUN apt-get install -y openjdk-11-jdk openjdk-11-jre
RUN apt-get install -y gcc g++ mono-complete mono-devel pypy3 unzip wget

WORKDIR /pascal
RUN wget "http://pascalabc.net/downloads/PascalABCNETLinux.zip"
RUN unzip "PascalABCNETLinux.zip" "PascalABCNETLinux/*"
RUN echo '#! /bin/sh' >> /bin/pabcnetc
RUN echo 'mono /pascal/PascalABCNETLinux/pabcnetcclear.exe $1' >> /bin/pabcnetc
RUN chmod u+x /bin/pabcnetc

WORKDIR ../rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs/ | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"

WORKDIR ../go
RUN wget "https://go.dev/dl/go1.20.5.linux-amd64.tar.gz" -O go.tar.gz
RUN tar -C /usr/local -xzf go.tar.gz
RUN export PATH=$PATH:/usr/local/go/bin

WORKDIR ../node
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
RUN nvm install 20.4


WORKDIR ..
RUN source ~/.bashrc
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./main.py"]