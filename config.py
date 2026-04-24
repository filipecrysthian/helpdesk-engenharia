import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = "troque-essa-chave-depois"
    SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(BASE_DIR, "instance", "helpdesk.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False