from flask import jsonify

from api.exceptions import InvalidFieldException, InvalidDataException
from . import main


@main.route('/')
def index():
    data = {
        "text": "hello there",
        "color": "blue"
    }
    return jsonify(data)


@main.app_errorhandler(403)
def forbidden(e):
    data = {
        "error": {
            "status": "403",
            "message": "Forbidden"
        }
    }
    return jsonify(data), 403


@main.app_errorhandler(404)
def page_not_found(e):
    data = {
        "error": "404",
        "message": "Page Not Found"
    }
    print("Error: ", e)
    return jsonify(data), 404


@main.app_errorhandler(500)
def internal_server_error(e):
    data = {
        "error": "500",
        "message": "Internal Server Error"
    }
    return jsonify(data), 500


@main.app_errorhandler(InvalidFieldException)
def not_found(e):
    data = {
        "error": "400",
        "message": "Invalid Field"
    }
    return jsonify(data), 400


@main.app_errorhandler(InvalidDataException)
def not_found(e):
    data = {
        "error": "400",
        "message": "Invalid Data"
    }
    return jsonify(data), 400