FROM python:3-alpine
MAINTAINER Graham Moore "graham.moore@sesam.io"

COPY ./service/datasource-service.py /service/
COPY ./service/requirements.txt /service/requirements.txt

WORKDIR /service
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

EXPOSE 5000/tcp
CMD ["python3", "-u", "./datasource-service.py"]
