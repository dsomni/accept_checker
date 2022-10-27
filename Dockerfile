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

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "./listener.py"]