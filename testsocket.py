import logging
import tornado.escape
import tornado.ioloop
import tornado.options
from tornado.web import RequestHandler
import tornado.websocket
import os.path
from os import listdir
import uuid

from tornado.options import define, options

define("port", default=8888, help="port to run on", type=int)
define("debug", default=False, help="run in debug mode", type=bool)


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/code", CodeHandler),
            (r"/codesocket", CodeSocketHandler),
            (r"/chatsocket", ChatSocketHandler),
        ]

        settings = dict(
            cookie_secret="my-test-socket-secret-cookie",
            template_path=os.path.join(os.path.dirname(__file__), "templates"),
            static_path=os.path.join(os.path.dirname(__file__), "static"),
            xsrf_cookies=True,
            debug=options.debug,
        )
        tornado.web.Application.__init__(self, handlers, **settings)

class CodeHandler(RequestHandler):
    def get(self):
        config = {
            "modes": self._find_ace_files("mode-"),
            "themes": self._find_ace_files("theme-"),
        }
        self.render("code.html", **config)

    def _find_ace_files(self, file_type):
        path = os.path.join(os.path.dirname(__file__), "static/ace")
        files = []
        for f in listdir(path):
            if f.startswith(file_type):
                file_name = f[len(file_type):-3]
                files.append(file_name)
        files.sort()
        print(files)
        return files


class MainHandler(RequestHandler):
    def get(self):
        self.render("index.html", messages=ChatSocketHandler.cache)


class CodeSocketHandler(tornado.websocket.WebSocketHandler):
    def __init__(self, *args, **kwargs):
        super(CodeSocketHandler, self).__init__(*args, **kwargs)
        self.waiters = set()
        self.cache = []
        self.cache_size = 50

    def open(self):
        self.waiters.add(self)

    def on_close(self):
        self.waiters.remove(self)

    def _update_cache(self, message):
        self.cache.append(message)
        if len(self.cache) > self.cache_size:
            self.cache = self.cache[-self.cache_size:]

    def _send_updates(self, message):
        logging.info("sending message to %d waiters" % len(self.waiters))
        for waiter in self.waiters:
            try:
                waiter.write_message(message)
            except:
                logging.error("Error sending message", exc_info=True)

    def on_message(self, message):
        logging.info("got message %r" % message)
        parsed = tornado.escape.json_decode(message)
        chat = {
            "id": str(uuid.uuid4()),
            "message": parsed,
        }
        self._update_cache(message)
        self._send_updates(message)


class ChatSocketHandler(tornado.websocket.WebSocketHandler):
    waiters = set()
    cache = []
    cache_size = 200

    def open(self):
        ChatSocketHandler.waiters.add(self)

    def on_close(self):
        ChatSocketHandler.waiters.remove(self)

    @classmethod
    def update_cache(cls, chat):
        cls.cache.append(chat)
        if len(cls.cache) > cls.cache_size:
            cls.cache = cls.cache[-cls.cache_size:]

    @classmethod
    def send_updates(cls, chat):
        logging.info("sending message to %d waiters", len(cls.waiters))
        for waiter in cls.waiters:
            try:
                waiter.write_message(chat)
            except:
                logging.error("Error sending message", exc_info=True)

    def on_message(self, message):
        logging.info("got message %r", message)
        parsed = tornado.escape.json_decode(message)
        chat = {
            "id": str(uuid.uuid4()),
            "body": parsed["body"],
        }
        chat["html"] = tornado.escape.to_basestring(
            self.render_string("message.html", message=chat))
        ChatSocketHandler.update_cache(chat)
        ChatSocketHandler.send_updates(chat)


def main():
    tornado.options.parse_command_line()
    app = Application()
    app.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
