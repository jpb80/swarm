#!/usr/bin/env python
# coding=utf-8

from flask import Flask
from flask import request
from flask import jsonify
import socket
import time

app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "OK"}), 200


@app.route("/get_node_ip", methods=["GET"])
def get_node_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return jsonify({'node_ip': s.getsockname()[0]}), 200


@app.route("/get_caller_ip", methods=["GET"])
def get_caller_ip():
    return jsonify({'ip': request.remote_addr}), 200


@app.route("/get_node_time", methods=["GET"])
def get_node_time():
    return jsonify({'time': time.time_ns()}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
