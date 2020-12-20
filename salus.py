from auth import OAuthToken, authenticate
from config import ConfigParser, read_config
from operator import attrgetter
from re import fullmatch
from sys import argv
from youtube import activities, subscriptions, unsubscribe

CONFIG = "./config.ini"
AGE_RE = "\\d+[my]"


class Subscription(object):

    def __init__(self, title: str, channel_id: str, sub_id: str):
        self.title = title
        self.channel_id = channel_id
        self.sub_id = sub_id


def to_secs(usr_input: str) -> int:
    multiplier = 30 if usr_input[-1] == "m" else 365
    return int(usr_input[:-1]) * multiplier * 24 * 60 * 60


def to_sub(subs: dict) -> [Subscription]:
    id_snips = [(sub["id"], sub["snippet"]) for sub in subs]
    resources = [(s_id, s["title"], s["resourceId"]) for s_id, s in id_snips]
    return [Subscription(title, r["channelId"], s_id) for s_id, title, r in resources]


def is_inactive(sub: Subscription, age: int, token: OAuthToken, cfg: ConfigParser) -> bool:
    channel_activities = activities(sub.channel_id, age, token, cfg)
    snippets = [activity["snippet"] for activity in channel_activities]
    return len(snippets) == 0


def delete_sub(sub: Subscription, token: OAuthToken, cfg: ConfigParser) -> None:
    if unsubscribe(sub.sub_id, token, cfg):
        print("Successfully unsubscribed from %s" % sub.title)
    else:
        print("Failed to unsubscribe from %s" % sub.title)


def main(age: int = 31000000):
    cfg = read_config(CONFIG)
    token = authenticate(cfg)
    subs = to_sub(subscriptions(token, cfg))
    inactive_subs = [sub for sub in subs if is_inactive(sub, age, token, cfg)]
    sorted_subs = sorted(list(set(inactive_subs)), key=attrgetter("title"))

    if len(sorted_subs) > 0:
        print("Following subscriptions have not uploaded recently: ")
        [print("- %s" % sub.title) for sub in sorted_subs]
        print()

        try:
            input("Press enter to continue; or ctrl-C to cancel")
            [delete_sub(sub, token, cfg) for sub in sorted_subs]
        except KeyboardInterrupt:
            print("Not deleting any subscriptions, exiting")
    else:
        print("No subscriptions have been dormant this long, exiting")


if __name__ == "__main__":
    if len(argv) < 2:
        print("Usage: salus.py MAX_AGE (e.g. 1d, 5y)")
    elif not fullmatch(AGE_RE, argv[1]):
        print("Invalid max age: accepts d (days) or y (years)")
    else:
        main(to_secs(argv[1]))
