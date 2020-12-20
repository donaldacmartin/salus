from configparser import ConfigParser
from http.server import HTTPServer, BaseHTTPRequestHandler
from json import loads
from time import time
from urllib.error import URLError
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import urlopen
from webbrowser import open

oauth_response = None


class OAuthHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        global oauth_response

        oauth_response = self.path
        self.send_response(200, "OK"),
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(bytes("Auth complete: you can close me now", "utf-8"))


class OAuthToken(object):

    def __init__(self, token: str, expiry: int, scope: str, token_type: str):
        self.token = token
        self.expiry = expiry
        self.scope = scope
        self.token_type = token_type

    def header(self):
        return {"Authorization": "Bearer %s" % self.token}


def _to_auth_url(cfg: ConfigParser) -> str:
    try:
        url = list(urlparse(cfg["AuthUrl"]))

        query = urlencode({
            "scope": cfg["Scope"],
            "response_type": cfg["ResponseType"],
            "redirect_uri": "http://127.0.0.1:%d" % int(cfg["LoopbackPort"]),
            "client_id": cfg["ClientId"]
        })

        url[4] = query
        return urlunparse(url)
    except ValueError as v:
        raise RuntimeError("Error creating authorisation URL: %s" % v)


def _await_auth_response(timeout_secs: int, loopback_port: int) -> dict:
    global oauth_response

    try:
        httpd = HTTPServer(("127.0.0.1", loopback_port), OAuthHandler)
        httpd.timeout = timeout_secs
        httpd.handle_request()

        if not oauth_response:
            raise TimeoutError
        else:
            return oauth_response

    except Exception as e:
        raise RuntimeError("Failed to get authorisation from browser: %s" % e)
    except TimeoutError:
        raise RuntimeError("Timed out while waiting for browser authorisation")


def _response_to_auth_code(response: str) -> str:
    try:
        query = response[2:] if response.startswith("/?") else response
        parsed_query = parse_qs(query)
        return parsed_query["code"][0]
    except (KeyError, ValueError) as v:
        raise RuntimeError("Failed to get auth code from response: %s" % v)


def get_auth_code(cfg: ConfigParser) -> str:
    oauth_cfg = cfg["oauth"]

    auth_url = _to_auth_url(oauth_cfg)
    open(auth_url)

    server_timeout = int(oauth_cfg["AuthServerTimeout"])
    port = int(oauth_cfg["LoopbackPort"])
    response = _await_auth_response(server_timeout, port)

    return _response_to_auth_code(response)


def _to_req_body(code: str, cfg: ConfigParser) -> dict:
    return {
            "code": code,
            "client_id": cfg["ClientId"],
            "client_secret": cfg["ClientSecret"],
            "grant_type": cfg["GrantType"],
            "redirect_uri": "http://127.0.0.1:%d" % int(cfg["LoopbackPort"])
        }


def _do_post(body: bytes, oauth_cfg: ConfigParser):
    res = urlopen(oauth_cfg["TokenUrl"], data=body)

    if res.status == 200:
        data = str(res.read(1024), "utf-8")
        return loads(data)
    else:
        raise AssertionError("Non-200 status returned: %s" % res.status)


def _post_for_token(cfg: ConfigParser, auth_code: str) -> dict:
    try:
        oauth_cfg = cfg["oauth"]
        body = _to_req_body(auth_code, oauth_cfg)
        post_body = bytes(urlencode(body), "utf-8")
        return _do_post(post_body, oauth_cfg)
    except (AssertionError, URLError, ValueError) as e:
        raise RuntimeError("Error POSTing for token: %s" % e)


def _to_auth_obj(token_dict: dict) -> OAuthToken:
    try:
        token = token_dict["access_token"]
        expiry = time() + int(token_dict["expires_in"])
        scope = token_dict["scope"]
        token_type = token_dict["token_type"]

        return OAuthToken(token, expiry, scope, token_type)
    except ValueError as v:
        raise RuntimeError("Error parsing access token: %s" % v)


def authenticate(config: ConfigParser) -> OAuthToken:
    auth_code = get_auth_code(config)
    token = _post_for_token(config, auth_code)
    return _to_auth_obj(token)
