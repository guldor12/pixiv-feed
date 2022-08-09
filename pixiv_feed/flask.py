import sqlite3, json
from pathlib import Path

from flask import g, Flask, request, abort, current_app
from . import NAME, MyAppPixivAPI, select_feed, db as db_
from .exceptions import *

app = Flask(NAME, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY="dev",
    DATABASE=Path(app.instance_path) / "cache.sqlite3",
)

Path(app.instance_path).mkdir(parents=True, exist_ok=True)


class FlaskAppPixivAPI(MyAppPixivAPI):
    def refresh(self):
        db = get_db()
        cur = db.cursor()
        cur.execute(
            "SELECT value, expires FROM data WHERE key=? LIMIT 1",
            ("pixiv",),
        )
        result = cur.fetchone()
        if result is None:
            raise PixivNotAuthorizedException
        value, expiry = result
        tokens = json.loads(value)
        try:
            self.refresh_token = tokens["refresh_token"]
            if self.refresh_token is None:
                raise PixivNotAuthorizedException
        except ValueError:
            raise PixivNotAuthorizedException
        self.access_token = tokens.get("access_token", None)

        return super().refresh()


pixiv = FlaskAppPixivAPI()


def get_db():
    if "db" not in g:
        g.db = db_.get_db(current_app.config["DATABASE"])
    return g.db


def close_db(e=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()


app.teardown_appcontext(close_db)


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
