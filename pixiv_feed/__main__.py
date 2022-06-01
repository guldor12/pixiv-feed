import sys
import click
from . import MyAppPixivAPI, select_feed
from .flask import app


@click.group(add_help_option=False)
@click.help_option("-h", "--help")
def cli():
    pass


def select_feed(fg, feed_type):
    if feed_type == "rss":
        return fg.rss_str()
    elif feed_type == "atom":
        return fg.atom_str()
    else:
        raise ValueError


# fmt: off
@cli.command(add_help_option=False, help="Generate and serve RSS/Atom feeds for Pixiv users")
@click.help_option("-h", "--help")
@click.option("-l", "--language", help="Language to serve feeds in")
@click.option("-r", "--rss", "feedtype", flag_value="rss", default=True,
              help="Generate RSS feed (default)")
@click.option("-a", "--atom", "feedtype", flag_value="atom", help="Generate Atom feed")
@click.argument("endpoint", type=click.Choice(("illust", "new_illust")))
# fmt: on
def generate(feedtype, endpoint, language):
    kwargs = {}
    if language is not None:
        kwargs["land"] = language

    pixiv = MyAppPixivAPI()

    if endpoint == "new_illust":
        sys.stdout.buffer.write(select_feed(pixiv.new_illusts_feed(**kwargs), feedtype))

    return 0


@cli.command(add_help_option=False, help="Generate and serve RSS/Atom feeds for Pixiv users")
@click.help_option("-h", "--help")
@click.option("--host", default="localhost", help="Host to bind to")
@click.option("-p", "--port", type=int, help="Port to serve feeds on")
def server(host, port):
    app.run(host=host, port=port)

    return 0


if __name__ == "__main__":
    sys.exit(cli())
