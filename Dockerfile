FROM python:3.4-alpine
ADD . /app
WORKDIR /app
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
