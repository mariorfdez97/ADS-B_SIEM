FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir requests

COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 9000
VOLUME ["/data"]

CMD ["/app/start.sh"]

