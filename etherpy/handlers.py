import os
import logging
import uuid
try:
    from urllib.parse import urlparse # py2
except ImportError:
    from urlparse import urlparse # py3


from  tornado import escape
from tornado.web import RequestHandler
from tornado.websocket import WebSocketHandler
import tornado.gen

from auth.github import GithubMixin


class DBMixin(object):
    def get_db_connection(self):
        return self.settings['db']

    def get_document_data(self, document_id):
        db = self.get_db_connection()
        return db.documents.find_one({"id":document_id})


class BaseHandler(RequestHandler, DBMixin):
    def get_current_user(self):
        user = self.get_secure_cookie("user")
        if user:
            return tornado.escape.json_decode(user)
        return None


class MainHandler(BaseHandler):
    def get(self):
        self.render("index.html")


class ProfileHandler(BaseHandler):
    def get(self, user_name):
        user = self.get_current_user()
        logging.info("user: %s" % user)
        self.render("profile.html", user=user)


class CodeHandler(BaseHandler):
    def get(self, document_id):
        # if self.get_current_user():
        #     self.get_current_user()['login']
        # else:
        #     ""
        config = {
            "modes": self._find_ace_files("mode-"),
            "themes": self._find_ace_files("theme-"),
            "user": self.get_current_user(),
            "document_data": self.get_document_data(document_id),
        }
        logging.info("document_data: %s" % config['document_data'])
        self.render("code.html", **config)

    def _find_ace_files(self, file_type):
        path = self.settings['static_path'] + "/ace"
        files = []
        for f in os.listdir(path):
            if f.startswith(file_type):
                file_name = f[len(file_type):-3]
                files.append(file_name)
        files.sort()
        return files


class NewCodeHandler(BaseHandler):
    def get(self):
        document_id = str(uuid.uuid4())
        self.redirect("/code/" + document_id)


class CodeSocketHandler(WebSocketHandler, DBMixin):
    waiters = set()
    cache = []
    cache_size = 50

    # TODO check the origin for XSS
    # def check_origin(self, origin):
    #     # call super.check_origin()
    #     parsed_origin = urlparse(origin)
    #     return parsed_origin.netloc.endswith("cp16net.net")

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
        if parsed['type'] == "delta_event":
            chat = {
                "id": str(uuid.uuid4()),
                "user_id": self.id,
                "message": parsed['data'],
            }
            CodeSocketHandler._update_cache(chat)
            CodeSocketHandler._send_updates(chat, self)
        elif parsed['type'] == "document_save":
            # user = self.get_current_user()
            # logging.info("got user: %s" % user)
            document = {
                # "user_id": user['_id'],
                "id": parsed['data']['id'],
                "body": parsed['data']['body'],
                "theme": parsed['data']['theme'],
                "mode": parsed['data']['mode'],
            }
            db = self.get_db_connection()
            db.documents.update(
                {"id": parsed['data']['id']},
                document,
                upsert=True
            )


class GithubLoginHandler(BaseHandler, GithubMixin):
    _OAUTH_REDIRECT_URL = 'http://localhost:8888/'

    @tornado.gen.coroutine
    def get(self):
        redirect_uri = tornado.httputil.url_concat(
            self._OAUTH_REDIRECT_URL + 'login',
            {'next': self.get_argument('next', '/code')}
        )
        if self.get_argument("code", False):
            logging.info("code arg: %r" % self.get_argument("code"))
            user = yield self.get_authenticated_user(
                redirect_uri=self._OAUTH_REDIRECT_URL + "code",
                client_id=self.settings["github_api_key"],
                client_secret=self.settings["github_secret"],
                code=self.get_argument("code"),
                extra_fields=self.settings["extra_fields"]
            )
            self._on_login(user)
            self.redirect(self.get_argument("next", u"/"))
        else:
            yield self.authorize_redirect(
                redirect_uri=redirect_uri,
                client_id=self.settings["github_api_key"],
                extra_params={
                    "scope": self.settings['github_scope'],
                }
            )

    def _on_login(self, user):
        login_user = tornado.escape.json_encode(user)
        logging.info(user)
        db = self.get_db_connection()
        db.users.update(
            {"login": user['login']},
            user,
            upsert=True
        )
        self.set_secure_cookie("user", login_user)


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect("/code")
