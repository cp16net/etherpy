import json
import logging
import os
import pymongo
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
from handlers import NewCodeHandler
from handlers import CodeSocketHandler
from handlers import LogoutHandler


# Utility code to retrieve Cloud Foundry production service information
if 'VCAP_APP_PORT' in os.environ:
    port = int(os.getenv('VCAP_APP_PORT'))
    j = json.loads(os.getenv('VCAP_SERVICES'))
    print(j)
    mongodb = j['mongodb'][0]
else:
    # this is localhost
    port = 8888
    mongodb = dict(options=dict(hostname='localhost',
                                port=27017,
                                db='db'))

define("port", default=port, help="run on the given port", type=int)
define("debug", default=False, help="run in debug mode", type=bool)

if 'username' in mongodb['credentials']:
    mongouri = 'mongodb://{username}:{password}@{hostname}:{port}/{db}'
else:
    mongouri = 'mongodb://{hostname}:{port}'
mongouri = mongouri.format(**mongodb['credentials'])
print('Connecting to %s' % mongouri)
mongo = pymongo.MongoClient(mongouri)
mongo_db = mongo.db

class EtherpyApplication(Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/login", GithubLoginHandler),
            (r"/logout", LogoutHandler),
            (r"/codesocket", CodeSocketHandler),
            (r"/code", NewCodeHandler),
            (r"/code/(.*)", CodeHandler),
            (r"/user/(.*)", ProfileHandler),
        ]

        print(os.path.dirname(__file__))
        template_path = os.path.join(os.path.dirname(__file__), "templates")
        static_path = os.path.join(os.path.dirname(__file__), "static")
        print(template_path)
        print(static_path)
        settings = dict(
            cookie_secret=secrets.COOKIE_SECRET,
            template_path=template_path,
            static_path=static_path,
            xsrf_cookies=True,
            debug=options.debug,
            github_api_key=secrets.GITHUB_CONSUMER_KEY,
            github_secret=secrets.GITHUB_CONSUMER_SECRET,
            github_scope="user:email,gist",
            extra_fields=[],
            db=mongo_db
        )
        Application.__init__(self, handlers, **settings)


def main():
#TODO(cp16net) change this to use a conf file
#    tor_options.parse_config_file("etherpy.conf")
    tor_options.parse_command_line()
    app = EtherpyApplication()
    app.listen(options.port)
    print("Server Running: http://%s:%s" % ("localhost", options.port))
    ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
