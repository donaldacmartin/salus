from auth import OAuthToken
from configparser import ConfigParser
from datetime import datetime, timedelta
from json import loads
from time import sleep
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse, urlunparse
from urllib.request import Request, urlopen


def _send_req(url: str, qry: dict, token: OAuthToken) -> dict:
    try:
        url_parts = list(urlparse(url))
        url_parts[4] = urlencode(qry)
        request = Request(urlunparse(url_parts), headers=token.header())
        response = urlopen(request)

        if response.status == 200:
            body = response.read()
            return loads(body)
        else:
            raise HTTPError("Non-OK response code: %d" % response.status)
    except HTTPError as e:
        print("Unexpected HTTP response: %s" % e)
    except ValueError as e:
        print("Error parsing response : %s\n\n%s" % (e, body))
    except URLError as e:
        print("Error trying to open %s : %e" % (url, e))

    return {}


def _delete(url: str, qry: dict, token: OAuthToken) -> bool:
    try:
        url_parts = list(urlparse(url))
        url_parts[4] = urlencode(qry)
        request = Request(urlunparse(url_parts), headers=token.header(), method="DELETE")
        response = urlopen(request)

        if response.status == 204:
            return True
        else:
            raise HTTPError("Non-OK response code: %d" % response.status)
    except HTTPError as e:
        print("Unexpected HTTP response: %s" % e)
    except URLError as e:
        print("Error trying to open %s : %e" % (url, e))

    return False


def subscriptions(token: OAuthToken, cfg: ConfigParser,
                  page: str = None) -> [dict]:
    yt_config = cfg["youtube"]
    url = yt_config["SubscriptionsUrl"]
    qry = {"part": "snippet", "mine": True, "maxResults": 50}
    page_sleep_secs = int(yt_config["PagingSleepSecs"])

    if page:
        qry["pageToken"] = page

    response = _send_req(url, qry, token)
    items = response["items"] if "items" in response else []

    if "nextPageToken" in response:
        print("Waiting %d seconds before next page" % page_sleep_secs)
        sleep(page_sleep_secs)
        return items + subscriptions(token, cfg, response["nextPageToken"])
    else:
        return items


def activities(channel_id: str, max_age: int, token: OAuthToken, cfg: ConfigParser) -> [dict]:
    yt_config = cfg["youtube"]
    url = yt_config["ActivitiesUrl"]
    since = (datetime.now() - timedelta(seconds=max_age)).strftime(yt_config["DateTimeFormat"])

    qry = {
        "part": "snippet",
        "channel_id": channel_id,
        "publishedAfter": since,
        "maxResults": 1
    }

    response = _send_req(url, qry, token)
    return response["items"] if "items" in response else []


def unsubscribe(sub_id: str, token: OAuthToken, cfg: ConfigParser) -> bool:
    yt_config = cfg["youtube"]
    url = yt_config["SubscriptionsUrl"]
    qry = {"id": sub_id}
    return _delete(url, qry, token)
