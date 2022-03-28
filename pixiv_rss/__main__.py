import sys, os, io, json, argparse
from time import time
from pathlib import Path
from urllib.parse import urlparse

from appdirs import AppDirs
from pixivpy3 import *
from flask import Flask, request
from feedgen.feed import FeedGenerator

__name__ = "pixiv-feedgen"

APPDIRS = AppDirs(__name__)
DATADIR = Path(APPDIRS.user_cache_dir)


def create_parser():
    parser = argparse.ArgumentParser()
    addarg = parser.add_argument

    # fmt: off
    addarg("--rss", dest="feed_type", action="store_const", const="rss", default="rss",
           help="Generate an RSS feed")
    addarg("--atom", dest="feed_type", action="store_const", const="atom",
           help="Generate an Atom feed")
    addarg("-p", "--port", action="store", type=int,
           help="Port to serve feeds on")
    # fmt: on

    return parser


def init_pixiv():
    app = AppPixivAPI()

    DATADIR.mkdir(parents=True, exist_ok=True)

    # get cached tokens
    with open(DATADIR / "token.json", "r+") as fp:
        try:
            cache = json.load(fp)
            app.set_auth(access_token=cache["access_token"])
        except JSONDecodeError:
            cache = None

        if cache is None or time() > cache["expiry"]:
            resp = app.auth(refresh_token=cache["refresh_token"])

            fp.seek(0, io.SEEK_SET)
            fp.truncate()

            json.dump(
                fp=fp,
                obj=dict(
                    access_token=app.access_token,
                    refresh_token=app.refresh_token,
                    expiry=int(time()) + resp["expires_in"],
                ),
                separators=(",", ":"),
            )

    return app


__PIXIV_USER_PATH_JP__ = "https://www.pixiv.net/users/{uid}"
__PIXIV_ARTWORK_PATH_JP__ = "https://www.pixiv.net/artworks/{uid}"
__PIXIV_USER_PATH__ = "https://www.pixiv.net/{language}/users/{uid}"
__PIXIV_ARTWORK_PATH__ = "https://www.pixiv.net/{language}/artworks/{uid}"


def create_feed(pixiv_app, user_id, language="en"):
    user_details = pixiv_app.user_detail(user_id)

    fg = FeedGenerator()
    if language == "jp":
        url_base = __PIXIV_USER_PATH_JP__
    else:
        url_base = __PIXIV_USER_PATH__
    url = url_base.format(uid=user_id, language=language)

    username = user_details['user']['name']
    fg.id(url)
    fg.title(f"{username} - Pixiv")
    fg.description(f"{username} - Pixiv")
    fg.author(name=username)
    fg.link(href=url)
    fg.logo("https://www.pixiv.net/favicon.ico")
    fg.language(language)

    return fg


def main():
    args = create_parser().parse_args()

    pixiv = init_pixiv()

    server = create_app(pixiv)

    server.run(port=args.port)


def create_app(pixiv_app):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=Path(app.instance_path) / "cache.sqlite",
    )

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    def get_feed():
        user_id = request.args["id"]
        language = request.args.get("lang")
        pixiv_app.set_accept_language(language)
        feed = create_feed(pixiv_app, user_id, language)

        for illust in pixiv_app.user_illusts(user_id)["illusts"]:
            fe = feed.add_entry()

            if language == "jp":
                url_base = __PIXIV_ARTWORK_PATH_JP__
            else:
                url_base = __PIXIV_ARTWORK_PATH__
            url = url_base.format(uid=illust["id"], language=language)

            fe.id(url)
            fe.title(illust["title"])
            fe.published(illust["create_date"])
            fe.content(illust["caption"], type="html")
            fe.link(href=url)

        return feed

    @app.route("/rss")
    def rss():
        return get_feed().rss_str()

    @app.route("/atom")
    def atom():
        return get_feed().atom_str()

    return app
