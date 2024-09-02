from flask import Flask
from flask_restx import Api
from .models.models import db
from flask_cors import CORS

from .controllers.controllers import api as ns1

app = Flask(__name__)
app.config.from_object('config')
db.init_app(app)
CORS(app)
api = Api(
    app,
    version="0.1",
    title=' Service APIs',
    doc='/swagger')

api.add_namespace(ns1, path='')