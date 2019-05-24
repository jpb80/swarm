#!/usr/bin/env python
# coding=utf-8

from flask import Flask
from flask import request
from flask import jsonify
import socket

app = Flask(__name__)


@app.route("/health")
def health_check():
    return "{\"status\":\"OK\"}", 200


@app.route("/get_node_ip", methods=["GET"])
def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0], 200


@app.route("/get_caller_ip", methods=["GET"])
def get_my_ip():
    return jsonify({'ip': request.remote_addr}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
