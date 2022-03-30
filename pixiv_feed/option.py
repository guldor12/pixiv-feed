import argparse

def create_parser():
    parser = argparse.ArgumentParser()
    addarg = parser.add_argument

    # fmt: off
    addarg("--rss", dest="feed_type", action="store_const", const="rss", default="rss",
           help="Generate an RSS feed")
    addarg("--atom", dest="feed_type", action="store_const", const="atom",
           help="Generate an Atom feed")
    addarg("--host", action="store",
           help="Host to bind to")
    addarg("-p", "--port", action="store", type=int,
           help="Port to serve feeds on")
    # fmt: on

    return parser
