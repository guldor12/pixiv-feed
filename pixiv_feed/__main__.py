import sys
import click
from . import flask_init


@click.command(add_help_option=False, help="Generate and serve RSS/Atom feeds for Pixiv users")
@click.help_option("-h", "--help")
@click.option("--host", default="localhost", help="Host to bind to")
@click.option("-p", "--port", type=int, help="Port to serve feeds on")
def main(host, port):
    server = flask_init()
    server.run(host=host, port=port)

    return 0


if __name__ == "__main__":
    sys.exit(main())
