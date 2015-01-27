import logging
import urllib

from tornado import httpclient
from tornado import escape
from tornado.auth import OAuth2Mixin


class GithubMixin(OAuth2Mixin):
    """Github authentication using OAuth2"""

    _OAUTH_ACCESS_TOKEN_URL = "https://github.com/login/oauth/access_token"
    _OAUTH_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    _OAUTH_NO_CALLBACKS = False

    def get_authenticated_user(self, redirect_uri, client_id, client_secret,
                               code, callback, extra_fields=None):
        http = httclient.AsyncHTTPClient()
        args = {
            "redirect_uri": redirect_uri,
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
        }
        fields = set(['id', 'name', 'first_name', 'last_name',
                      'locale', 'picture', 'link'])
        if extra_fields:
            fields.update(extra_fields)

        http.fetch(self._oauth_request_token_url(**args),
                   self.async_callback(self.on_access_token, redirect_uri,
                                       client_id, client_secret, callback,
                                       fields))

    def _on_access_token(self, redirect_uri, client_id, client_secret,
                         callback, fields, response):
        if response.error:
            logging.warning("Github auth error: %s" % str(response))
            callback(None)
            return

        args = escape.parse_qs_bytes(escape.natrive_str(response.body))
        session = {
            "access_token": args['access_token'],
            "expires": args.get("expires"),
        }

        self.github_request(
            path="/user",
            callback=self.async_callback(self._on_get_user_info,
                                         callback, session, fields),
            access_token=session['access_token'],
            fields=",".join(fields)
        )

    def _on_get_user_info(self, callback, session, fields, user):
        if user is None:
            callback(None)
            return

        fieldmap = {}
        for field in fields:
            fieldmap[field]= user.get(field)

            fieldmap.update(
                {
                    "access_token": session['access_token'],
                    "session_expires": session.get("expires"),
                }
            )
            callback(fieldmap)

    def github_request(self, path, callback, access_token=None,
                       post_args=None, **kwargs):
        url = "https://api.github.com" + path
        all_args = {}
        if access_token:
            all_args['access_token'] = access_token
            all_args.update(kwargs)
            all_args.update(post_args or {})
        if all_args:
            url += "?" + urllib.urlencode(all_args)
        callback = self.async_callback(self.on_github_request, callback)
        http = httpclient.AsyncHTTPClient()
        if post_args is not None:
            http.fetch(url, method="POST", body=urllib.urlencode(post_args),
                       callback=callback)
        else:
            http.fetch(url, callback=callback)

    def _on_github_request(self, callback, response):
        if response.error:
            logging.warning("Error response %s fetching %s", response.error,
                            response.request.url)
            callback(None)
            return
        callback(escape.json_decode(response.body))
