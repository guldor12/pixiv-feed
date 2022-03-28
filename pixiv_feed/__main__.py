import sys, os, io, json, html, argparse
from time import time
from pathlib import Path
from urllib.parse import urlparse, quote as urlquote

from appdirs import AppDirs
from pixivpy3 import *
from flask import Flask, request
from feedgen.feed import FeedGenerator

__name__ = "pixiv-feed"

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
__PIXIV_TAG_PATH_JP__ = "https://www.pixiv.net/tags/{}"
__PIXIV_TAG_PATH__ = "https://www.pixiv.net/en/tags/{}"


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
        name = request.args.get("name")
        pixiv_app.set_accept_language(language)

        user_details = pixiv_app.user_detail(user_id)

        feed = FeedGenerator()
        if language == "jp":
            url_base = __PIXIV_USER_PATH_JP__
        else:
            url_base = __PIXIV_USER_PATH__
        url = url_base.format(uid=user_id, language=language)

        username = user_details["user"]["name"]
        title = f"{name or username} - Pixiv"

        feed.id(url)
        feed.title(title)
        feed.description(title)
        feed.author(name=username)
        feed.link(href=url)
        feed.logo("https://www.pixiv.net/favicon.ico")
        feed.language(language)

        for illust in pixiv_app.user_illusts(user_id)["illusts"]:
            fe = feed.add_entry()

            if language == "jp":
                url_base = __PIXIV_ARTWORK_PATH_JP__
            else:
                url_base = __PIXIV_ARTWORK_PATH__
            url = url_base.format(uid=illust["id"], language=language)

            body = ""
            if illust["caption"]:
                body += "{caption}<br/><br/>"
            tags = []
            for tag in illust["tags"]:
                if language == "jp":
                    tag_url_base = __PIXIV_TAG_PATH_JP__
                else:
                    tag_url_base = __PIXIV_TAG_PATH__
                tag_url = tag_url_base.format(urlquote(tag["name"]))

                tag_body = f"#{tag['name']}"
                if tag["translated_name"] is not None:
                    tag_body += f" {tag['translated_name']}"
                tag_body = html.escape(tag_body)
                tags.append(f"<a href={tag_url}>{tag_body}</a>")
            body += " ".join(tags)
            body = body.format(**illust)

            fe.id(url)
            fe.title(illust["title"])
            fe.published(illust["create_date"])
            fe.content(body, type="html")
            fe.link(href=url)

        return feed

    @app.route("/rss")
    def rss():
        return get_feed().rss_str()

    @app.route("/atom")
    def atom():
        return get_feed().atom_str()

    return app
