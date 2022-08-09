import sys
import click
from . import MyAppPixivAPI, select_feed
from .flask import app
from .auth import login as pixiv_login


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
@cli.command(add_help_option=False, help="Generate and serve RSS/Atom feeds for Pixiv users",
             no_args_is_help=True)
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


@cli.command(add_help_option=False, help="Generate and serve RSS/Atom feeds for Pixiv users")
@click.help_option("-h", "--help")
@click.option("--host", default="localhost", help="Host to bind to")
@click.option("-p", "--port", type=int, help="Port to serve feeds on")
def server(host, port):
    app.run(host=host, port=port)


@cli.command(
    add_help_option=False,
    short_help="Obtain authentication tokens",
    help="Open a browser to obtain API tokens",
)
@click.help_option("-h", "--help")
def login():
    auth_data = pixiv_login()
    pixiv = MyAppPixivAPI()
    pixiv.set_auth(auth_data["access_token"], auth_data["refresh_token"])
    pixiv.refresh()


@cli.command(
    add_help_option=False,
    short_help="Insert authentication tokens",
    help="Insert authentication tokens from command line",
)
@click.help_option("-h", "--help")
@click.argument("refresh_token")
def refresh(refresh_token):
    pixiv = MyAppPixivAPI()
    pixiv.refresh_token = refresh_token
    pixiv.refresh()


if __name__ == "__main__":
    sys.exit(cli())
