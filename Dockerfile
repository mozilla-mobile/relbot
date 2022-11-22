FROM python:3.9

WORKDIR /usr/src/app

COPY requirements/base.txt requirements.txt
RUN pip install --no-cache-dir --require-hashes -r requirements.txt

COPY src/* ./

ENTRYPOINT ["/usr/src/app/relbot.py"]
