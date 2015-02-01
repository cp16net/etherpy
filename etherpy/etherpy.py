import logging
import os
from pymongo import MongoClient
import uuid

from tornado import escape
from tornado import ioloop
from tornado import options as tor_options
from tornado.options import define
from tornado.options import options

from tornado.web import Application
from tornado.websocket import WebSocketHandler
import tornado.httputil
import tornado.gen

from auth.github import GithubMixin
import secrets
from handlers import MainHandler
from handlers import GithubLoginHandler
from handlers import ProfileHandler
from handlers import CodeHandler
from handlers import CodeSocketHandler
from handlers import LogoutHandler

define("port", default=8888, help="port to run on", type=int)
define("debug", default=False, help="run in debug mode", type=bool)


class EtherpyApplication(Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/login", GithubLoginHandler),
            (r"/logout", LogoutHandler),
            (r"/code", CodeHandler),
            (r"/codesocket", CodeSocketHandler),
            (r"/user/(.*)", ProfileHandler),
        ]

        client = MongoClient(secrets.MONGO_HOST, secrets.MONGO_PORT)

        settings = dict(
            cookie_secret=secrets.COOKIE_SECRET,
            template_path=os.path.join(os.path.dirname(__file__), "../templates"),
            static_path=os.path.join(os.path.dirname(__file__), "../static"),
            xsrf_cookies=True,
            debug=options.debug,
            github_api_key=secrets.GITHUB_CONSUMER_KEY,
            github_secret=secrets.GITHUB_CONSUMER_SECRET,
            github_scope="user:email,gist",
            extra_fields=[],
            db=client.etherpy
        )
        Application.__init__(self, handlers, **settings)


def main():
#TODO(cp16net) change this to use a conf file
#    tor_options.parse_config_file("etherpy.conf")
    tor_options.parse_command_line()
    app = EtherpyApplication()
    app.listen(options.port)
    ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
