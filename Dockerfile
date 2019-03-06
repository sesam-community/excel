FROM python:3-alpine
MAINTAINER Graham Moore "graham.moore@sesam.io"
COPY ./service /service
WORKDIR /service

RUN apk update
RUN apk add python-dev libxml2-dev libxslt-dev py-lxml musl-dev openssl-dev libffi-dev gcc

RUN pip install --upgrade pip

RUN pip install -r requirements.txt
EXPOSE 5000/tcp
ENTRYPOINT ["python"]
CMD ["datasource-service.py"]
