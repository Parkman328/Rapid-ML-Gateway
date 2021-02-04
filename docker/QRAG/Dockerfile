FROM python:3

WORKDIR /app

COPY ./app/requirements.txt .

RUN apt-get update \
  && pip install --upgrade pip  \
  && pip install -r requirements.txt \
  && rm -rf /var/cache/apk/*

RUN git clone https://github.com/Parkman328/QRAG-Docker.git
COPY /app/install/sagemaker/qrag.ini /app/QRAG-Docker/sagemaker/config
COPY /app/install/precog/qrag.ini /app/QRAG-Docker/precog/config
COPY /app/install/cognitive_services/qrag.ini /app/QRAG-Docker/cognitive_services/config

