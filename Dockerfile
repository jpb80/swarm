FROM python:3.7.3-alpine3.9
ADD . /app
WORKDIR /app
RUN pip install -r requirements.txt && \
    apk --update add curl
CMD ["python", "app.py"]
HEALTHCHECK CMD curl --fail 127.0.0.1:8000/health || exit 1
