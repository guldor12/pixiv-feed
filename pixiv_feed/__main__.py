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

    return 0


@cli.command(add_help_option=False, help="Generate and serve RSS/Atom feeds for Pixiv users")
@click.help_option("-h", "--help")
@click.option("--host", default="localhost", help="Host to bind to")
@click.option("-p", "--port", type=int, help="Port to serve feeds on")
def server(host, port):
    app.run(host=host, port=port)

    return 0


# fmt: off
@cli.command(add_help_option=False, short_help="Obtain authentication tokens", help="""
    1. Run the command. This will open the browser with Pixiv login page.

    2. Open dev console (F12) and switch to network tab.

    3. Enable persistent logging ("Preserve log").

    4. Type into the filter field: callback?

    5. Proceed with Pixiv login.

    \b
    6. After logging in you should see a blank page and request that looks like this:

    \b
       https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback?state=...&code=....

       Copy value of the code param into the pixiv_auth.py's prompt and hit the Enter key.

    If you did everything right and Pixiv did not change their auth flow, pair of auth_token and refresh_token should be displayed.

    \b
    WARNING:
    The lifetime of code is extremely short, so make sure to minimize delay
    between step 5 and 6. Otherwise, repeat everything starting step 1.
"""
)
@click.help_option("-h", "--help")
# fmt: on
def login():
    auth_data = pixiv_login()
    pixiv = MyAppPixivAPI()
    pixiv.set_auth(auth_data["access_token"], auth_data["refresh_token"])
    pixiv.refresh()

    return 0


@cli.command(add_help_option=False, help="Add authentication tokens")
@click.help_option("-h", "--help")
@click.argument("refresh_token")
def refresh(refresh_token):
    pixiv = MyAppPixivAPI()
    pixiv.refresh_token = refresh_token
    pixiv.refresh()

    return 0


if __name__ == "__main__":
    sys.exit(cli())
