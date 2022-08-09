from pathlib import Path

from flask import Flask, request, abort
from . import NAME, DATADIR, MyAppPixivAPI, select_feed

pixiv = MyAppPixivAPI()

app = Flask(NAME, instance_path=DATADIR)
app.config.from_mapping(
    SECRET_KEY="dev",
    DATABASE=Path(app.instance_path) / "cache.sqlite3",
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
