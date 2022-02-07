FROM python:3-alpine
MAINTAINER Hans Erlend Bakken Glad "hans.glad@sesam.io"

WORKDIR /service
COPY ./service/requirements.txt /service/requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY ./service/datasource-service.py /service/

EXPOSE 5000/tcp
CMD ["python3", "-u", "./datasource-service.py"]
