FROM tiangolo/uwsgi-nginx-flask:python3.8-alpine
RUN apk add g++
RUN apk add linux-headers
RUN apk add libc-dev
RUN apk add musl-dev
COPY requirements.txt /
RUN python -m pip install --upgrade pip
RUN pip install -r /requirements.txt
COPY . /
WORKDIR /
ENV PORT 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--worker-class", "eventlet", "app:app"]

