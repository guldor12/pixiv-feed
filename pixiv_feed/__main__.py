import sys, io, json, html
from time import time
from pathlib import Path
from urllib.parse import urlparse, quote as urlquote

from appdirs import AppDirs
from pixivpy3 import *
from flask import Flask, request
from feedgen.feed import FeedGenerator

from . import option

NAME = "pixiv-feed"

APPDIRS = AppDirs(NAME)
CACHEDIR = Path(APPDIRS.user_cache_dir)
DATADIR = Path(APPDIRS.user_data_dir)


class MyAppPixivAPI(AppPixivAPI):
    __PIXIV_ARTWORK_PATH_JP__ = "https://www.pixiv.net/artworks/{uid}"
    __PIXIV_ARTWORK_PATH__ = "https://www.pixiv.net/{language}/artworks/{uid}"
    __PIXIV_USER_PATH_JP__ = "https://www.pixiv.net/users/{uid}"
    __PIXIV_USER_PATH__ = "https://www.pixiv.net/{language}/users/{uid}"
    __PIXIV_TAG_PATH_JP__ = "https://www.pixiv.net/tags/{}"
    __PIXIV_TAG_PATH__ = "https://www.pixiv.net/en/tags/{}"

    def __init__(self, *kargs, **kwargs):
        self.expiry = None
        return super().__init__(*kargs, **kwargs)

    def _format(self, str_l, str_j, uid, lang):
        if lang is not None:
            return str_l.format(language=lang, uid=uid)
        else:
            return str_j.format(uid)

    def user_format(self, uid, lang=None):
        l = self.__PIXIV_USER_PATH__
        j = self.__PIXIV_USER_PATH_JP__
        return self._format(l, j, uid, lang)

    def illust_format(self, uid, lang=None):
        l = self.__PIXIV_ARTWORK_PATH__
        j = self.__PIXIV_ARTWORK_PATH_JP__
        return self._format(l, j, uid, lang)

    def tag_format(self, uid, lang=None):
        l = self.__PIXIV_TAG_PATH__
        j = self.__PIXIV_TAG_PATH_JP__
        return self._format(l, j, uid, lang)

    def user_feedgen(self, **kwargs):
        assert "id" in kwargs or "id_" in kwargs

        user_id = kwargs.get("id", kwargs.get("id_"))
        language = kwargs.get("lang")
        name = kwargs.get("name")
        self.set_accept_language(language)

        if not self.expiry or time() > self.expiry:
            # TODO: log
            refresh_pixiv(self)

        user_details = self.user_detail(user_id)

        fg = FeedGenerator()
        url = self.user_format(user_id, language)

        username = user_details["user"]["name"]
        title = f"{name or username} - Pixiv"

        fg.id(url)
        fg.title(title)
        fg.description(title)
        fg.author(name=username)
        fg.link(href=url)
        fg.logo("https://www.pixiv.net/favicon.ico")
        fg.language(language)

        for illust in self.user_illusts(user_id)["illusts"]:
            fe = fg.add_entry()

            url = self.illust_format(illust["id"], language)

            body = ""
            if illust["caption"]:
                body += "{caption}<br/><br/>"
            tags = []
            for tag in illust["tags"]:
                tag_url = self.tag_format(urlquote(tag["name"]))

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

        return fg


def refresh_pixiv(app):
    CACHEDIR.mkdir(parents=True, exist_ok=True)

    # get cached tokens
    with open(CACHEDIR / "token.json", "r+") as fp:
        cache = None
        if app.access_token is None or app.refresh_token is None:
            cache = json.load(fp)
            app.set_auth(cache["access_token"], cache["refresh_token"])

        # TODO: fixup
        if cache is None or time() > cache["expiry"]:
            resp = app.auth(refresh_token=app.refresh_token)

            app.expiry = int(time()) + resp["expires_in"]

            fp.seek(0, io.SEEK_SET)
            fp.truncate(0)

            json.dump(
                fp=fp,
                obj=dict(
                    access_token=app.access_token,
                    refresh_token=app.refresh_token,
                    expiry=app.expiry,
                ),
                separators=(",", ":"),
            )


def flask_init():
    pixiv = MyAppPixivAPI()

    app = Flask(__name__, instance_path=DATADIR)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=Path(app.instance_path) / "cache.sqlite",
    )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    @app.route("/rss")
    def rss():
        return pixiv.user_feedgen(**request.args).rss_str()

    @app.route("/atom")
    def atom():
        return pixiv.user_feedgen(**request.args).atom_str()

    return app


def main():
    args = option.create_parser().parse_args()

    server = flask_init()

    server.run(host=args.host, port=args.port)

    return 0


if __name__ == "__main__":
    sys.exit(main())
