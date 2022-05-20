import sys, io, json, html
from time import time
from pathlib import Path
from urllib.parse import urlparse, quote as urlquote

from appdirs import AppDirs
from pixivpy3 import *
from flask import Flask, request, abort
from feedgen.feed import FeedGenerator

NAME = "pixiv-feed"

APPDIRS = AppDirs(NAME)
CACHEDIR = Path(APPDIRS.user_cache_dir)
DATADIR = Path(APPDIRS.user_data_dir)


class UserNotFound(Exception):
    def __init__(self, uid):
        self.uid = uid
        self.message = f"User not found: {uid}"
        super().__init__(self.message)


class MyAppPixivAPI(AppPixivAPI):
    __PIXIV_ARTWORK_PATH_JP__ = "https://www.pixiv.net/artworks/{uid}"
    __PIXIV_ARTWORK_PATH__ = "https://www.pixiv.net/{language}/artworks/{uid}"
    __PIXIV_USER_PATH_JP__ = "https://www.pixiv.net/users/{uid}"
    __PIXIV_USER_PATH__ = "https://www.pixiv.net/{language}/users/{uid}"
    __PIXIV_TAG_PATH_JP__ = "https://www.pixiv.net/tags/{uid}"
    __PIXIV_TAG_PATH__ = "https://www.pixiv.net/{language}/tags/{uid}"

    __PIXIV_NEW_ILLUST_PATH__ = "https://www.pixiv.net/bookmark_new_illust.php"

    def __init__(self, *kargs, **kwargs):
        self.expiry = None
        return super().__init__(*kargs, **kwargs)

    def refresh(self):
        CACHEDIR.mkdir(parents=True, exist_ok=True)

        # get cached tokens
        with open(CACHEDIR / "token.json", "r+") as fp:
            cache = None
            if self.access_token is None or self.refresh_token is None:
                cache = json.load(fp)
                self.set_auth(cache["access_token"], cache["refresh_token"])
                self.user_id = cache["user_id"]

            # TODO: fixup
            if cache is None or time() > cache["expiry"]:
                resp = self.auth(refresh_token=self.refresh_token)

                self.expiry = int(time()) + resp["expires_in"]

                fp.seek(0, io.SEEK_SET)
                fp.truncate(0)

                json.dump(
                    fp=fp,
                    obj=dict(
                        user_id=self.user_id,
                        access_token=self.access_token,
                        refresh_token=self.refresh_token,
                        expiry=self.expiry,
                    ),
                    separators=(",", ":"),
                )

    def _format(self, str_l, str_j, uid, lang):
        if lang is not None and lang != "jp":
            return str_l.format(language=lang, uid=uid)
        else:
            return str_j.format(uid=uid)

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

    def tag_html(self, tag):
        url = self.tag_format(urlquote(tag["name"]))
        url = html.escape(url)

        tag_html = f"#{tag['name']}"
        if tag["translated_name"] is not None:
            tag_html += f" {tag['translated_name']}"
        tag_html = html.escape(tag_html)
        tag_html = f"<a href={url}>{tag_html}</a>"

        return tag_html

    def illust_html(self, illust):
        body = ""
        if illust["caption"]:
            body += "{caption}<br/><br/>"
        tags = []
        for tag in illust["tags"]:
            tags.append(self.tag_html(tag))
        body += " ".join(tags)
        body = body.format(**illust)

        return body

    def user_illusts_feed(self, **kwargs):
        assert "id" in kwargs or "id_" in kwargs

        user_id = kwargs.get("id", kwargs.get("id_"))
        language = kwargs.get("lang", "jp")
        name = kwargs.get("name")
        self.set_accept_language(language)

        if not self.expiry or time() > self.expiry:
            # TODO: log
            self.refresh()

        user_details = self.user_detail(user_id)

        if "user" not in user_details:
            raise UserNotFound(user_id)

        fg = FeedGenerator()
        url = self.user_format(user_id, language)

        username = user_details["user"]["name"]
        title = f"Pixiv - {name or username}"

        fg.id(url)
        fg.title(title)
        fg.description(title)
        fg.author(name=username)
        fg.link(href=url, rel="alternate")
        fg.logo("https://www.pixiv.net/favicon.ico")
        fg.language(language)

        for illust in self.user_illusts(user_id)["illusts"]:
            url = self.illust_format(illust["id"], language)

            body = self.illust_html(illust)

            fe = fg.add_entry()

            fe.id(url)
            fe.title(illust["title"])
            fe.author(name=f"{illust['user']['name']} ({illust['user']['account']})")
            fe.published(illust["create_date"])
            fe.content(body, type="html")
            fe.link(href=url)

        return fg

    def new_illusts_feed(self, **kwargs):
        language = kwargs.get("lang", "jp")
        self.set_accept_language(language)

        if not self.expiry or time() > self.expiry:
            # TODO: log
            self.refresh()

        user_details = self.user_detail(self.user_id)

        if "user" not in user_details:
            raise UserNotFound(self.user_id)

        fg = FeedGenerator()
        url = self.__PIXIV_NEW_ILLUST_PATH__

        username = user_details["user"]["name"]
        title = f"Pixiv - Works by users you're following - {username}"

        fg.id(url)
        fg.title(title)
        fg.description(title)
        fg.author(name=username)
        fg.link(href=url, rel="alternate")
        fg.logo("https://www.pixiv.net/favicon.ico")
        fg.language(language)

        for illust in self.illust_follow()["illusts"]:
            url = self.illust_format(illust["id"], language)

            body = self.illust_html(illust)

            fe = fg.add_entry()

            fe.id(url)
            fe.title(illust["title"])
            fe.author(name=f"{illust['user']['name']} ({illust['user']['account']})")
            fe.published(illust["create_date"])
            fe.content(body, type="html")
            fe.link(href=url)

        return fg


def select_feed(fg, feed_type):
    if feed_type == "rss":
        return fg.rss_str()
    elif feed_type == "atom":
        return fg.atom_str()
    else:
        raise ValueError



def flask_init():
    pixiv = MyAppPixivAPI()

    app = Flask(NAME, instance_path=DATADIR)
    app.config.from_mapping(
        SECRET_KEY="dev",
        DATABASE=Path(app.instance_path) / "cache.sqlite",
    )

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    def wrapper(func, *kargs, **kwargs):
        try:
            return func(*kargs, **kwargs)
        except ValueError:
            abort(404)

    @app.route("/illust/<feed_type>")
    def illust(feed_type):
        fg = pixiv.user_illusts_feed(**request.args)
        return wrapper(select_feed, fg, feed_type)

    @app.route("/new_illust/<feed_type>")
    def new_illust(feed_type):
        fg = pixiv.new_illusts_feed(**request.args)
        return wrapper(select_feed, fg, feed_type)

    return app
