import logging
import os
import uuid

from tornado import escape
from tornado import ioloop
from tornado import options as tor_options
from tornado.options import define
from tornado.options import options
from tornado.web import RequestHandler
from tornado.websocket import WebSocketHandler

from etherpy.auth.github import GithubMixin
from etherpy import secrets

define("port", default=8888, help="port to run on", type=int)
define("debug", default=False, help="run in debug mode", type=bool)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/login", GithubLoginHandler),
            (r"/code", CodeHandler),
            (r"/codesocket", CodeSocketHandler),
        ]

        settings = dict(
            cookie_secret=secrets.COOKIE_SECRET,
            template_path=os.path.join(os.path.dirname(__file__), "../templates"),
            static_path=os.path.join(os.path.dirname(__file__), "../static"),
            xsrf_cookies=True,
            debug=options.debug,
            github_api_key=secrets.GITHUB_CONSUMER_KEY,
            github_secret=secrets.GITHUB_CONSUMER_SECRET,            
        )
        tornado.web.Application.__init__(self, handlers, **settings)

class MainHandler(RequestHandler):
    def get(self):
        self.render("index.html")

        
class CodeHandler(RequestHandler):
    def get(self):
        config = {
            "modes": self._find_ace_files("mode-"),
            "themes": self._find_ace_files("theme-"),
        }
        self.render("code.html", **config)

    def _find_ace_files(self, file_type):
        path = self.settings[static_path] + "/ace"
        files = []
        for f in os.listdir(path):
            if f.startswith(file_type):
                file_name = f[len(file_type):-3]
                files.append(file_name)
        files.sort()
        return files


class CodeSocketHandler(WebSocketHandler):
    waiters = set()
    cache = []
    cache_size = 50

    def open(self):
        self.id = str(uuid.uuid4())
        CodeSocketHandler.waiters.add(self)

    def on_close(self):
        CodeSocketHandler.waiters.remove(self)

    @classmethod
    def _update_cache(cls, message):
        cls.cache.append(message)
        if len(cls.cache) > cls.cache_size:
            cls.cache = cls.cache[-cls.cache_size:]

    @classmethod
    def _send_updates(cls, message, ignore):
        logging.info("sending message to %d waiters" % len(cls.waiters))
        logging.info("sending message %r" % message)
        for waiter in cls.waiters:
            try:
                if waiter == ignore or message['user_id'] == waiter.id:
                    logging.info("found socket to ignore")
                    continue
                waiter.write_message(message['message'])
            except:
                logging.error("Error sending message", exc_info=True)

    def on_message(self, message):
        logging.info("got message %r" % message)
        logging.info("self: %r" % self.__dict__)
        parsed = escape.json_decode(message)
        chat = {
            "id": str(uuid.uuid4()),
            "user_id": self.id,
            "message": parsed,
        }
        CodeSocketHandler._update_cache(chat)
        CodeSocketHandler._send_updates(chat, self)


class GithubLoginHandler(RequestHandler, GithubMixin):
    _OAUTH_REDIRECT_URL = 'http://localhost:8888/auth/github'
    
    @tornado.web.asynchronous
    def get(self):
        if self.get_argument("code", False):
            self.get_authenticated_user(
                redirect_uri='/auth/github/',
                client_id=self.settings["github_api_key"],
                client_secret=self.settings["github_secret"],
                code=self.get_argument("code"),
                callback=self.async_callback(self._on_login))
            return
        self.authorize_redirect(redirect_uri='/auth/github/',
                                client_id=self.settings["github_api_key"],
                                extra_params={"scope": "read_stream,offline_access"})
        
    def _on_login(self, user):
        logging.debug(user)
        self.finish()


def main():
    tor_options.parse_command_line()
    app = Application()
    app.listen(options.port)
    ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
