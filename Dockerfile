FROM alpine:3 as db
WORKDIR /build
RUN apk add sqlite
COPY schema.sql .
RUN sqlite3 dispatch.db <schema.sql

############################

FROM python:3
EXPOSE 5000
WORKDIR /app
VOLUME /data

ENV DISPATCH_DATABASE=/data/dispatch.db
ENV BIND_PORT=5000
ENV BIND_HOST=0.0.0.0

COPY requirements.txt /build/requirements.txt
RUN pip install -r /build/requirements.txt

COPY app.py .

COPY --from=db /build/dispatch.db /build/dispatch.db

COPY entrypoint.sh /
ENTRYPOINT ["/entrypoint.sh"]
#ENTRYPOINT ["flask", "run", "--host", "0.0.0.0", "--port", "5000"]
