import functools
import logging
import urllib

from tornado import httpclient
from tornado import escape
from tornado.auth import OAuth2Mixin
from tornado.auth import _auth_return_future
from tornado.auth import AuthError


class GithubMixin(OAuth2Mixin):
    """Github authentication using OAuth2"""

    _OAUTH_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
    _OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    _OAUTH_NO_CALLBACKS = False
    _GITHUB_BASE_URL = "https://api.github.com"

    @_auth_return_future
    def get_authenticated_user(self, redirect_uri, client_id, client_secret,
                               code, callback, extra_fields=None):
        http = httpclient.AsyncHTTPClient()
        args = {
            "redirect_uri": redirect_uri,
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        fields = set(["id", "login", "name", "email",
                      "location", "url", "gists_url"])
        if extra_fields:
            fields.update(extra_fields)

        http.fetch(self._oauth_request_token_url(**args),
                   functools.partial(self._on_access_token, redirect_uri,
                                     client_id, client_secret, callback,
                                     fields))

    def _on_access_token(self, redirect_uri, client_id, client_secret,
                         future, fields, response):
        if response.error:
            future.set_exception(
                AuthError("Github auth error: %s" % str(response)))
            return
        logging.info("response: %r" % response)
        logging.info("response.body: %r" % response.body)
        args = escape.parse_qs_bytes(escape.native_str(response.body))
        logging.info("args: %r" % args)
        session = {
            "access_token": args['access_token'][0],
            "expires": args.get("expires"),
        }

        logging.info("session: %s" % session)
        self.github_request(
            path="/user",
            callback=functools.partial(self._on_get_user_info,
                                       future, session, fields),
            access_token=session['access_token'],
            fields=",".join(fields)
        )

    def _on_get_user_info(self, future, session, fields, user):
        if user is None:
            future.set_result(None)
            return
        logging.info("session: %r" % session)
        fieldmap = {}
        for field in fields:
            fieldmap[field]= user.get(field)

            fieldmap.update(
                {
                    "access_token": session['access_token'],
                    "session_expires": session.get("expires"),
                }
            )
        logging.info("fieldmap: %r" % fieldmap)
        logging.info("fields: %r" % fields)
        logging.info("user: %r" % user)
        future.set_result(fieldmap)

    @_auth_return_future
    def github_request(self, path, callback, access_token=None,
                       post_args=None, **args):
        url = self._GITHUB_BASE_URL + path
        all_args = {}
        if access_token:
            all_args['access_token'] = access_token
            all_args.update(args)

        if all_args:
            url += "?" + urllib.urlencode(all_args)
        callback = functools.partial(self._on_github_request, callback)
        http = httpclient.AsyncHTTPClient()
        logging.info("http connection: %s" % http)
        if post_args is not None:
            http.fetch(url, method="POST", body=urllib.urlencode(post_args),
                       callback=callback)
        else:
            http.fetch(url, callback=callback, user_agent="Etherpy")

    def _on_github_request(self, future, response):
        if response.error:
            future.set_exception(AuthError("Error response: %s" % response,
                                           response.error,
                                           response.request.url,
                                           response.body))
            return
        future.set_result(escape.json_decode(response.body))
