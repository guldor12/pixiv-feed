import argparse

def create_parser():
    parser = argparse.ArgumentParser()
    addarg = parser.add_argument

    # fmt: off
    addarg("--host", action="store",
           help="Host to bind to")
    addarg("-p", "--port", action="store", type=int,
           help="Port to serve feeds on")
    # fmt: on

    return parser
