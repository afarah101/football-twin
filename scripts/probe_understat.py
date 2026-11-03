"""One live Understat call, to watch whether GitHub Actions can reach the site (issues #2 and #13).

Exits 0 only on HTTP 200 with rows. Prints field names only: no values, no player names, no row counts. Saves nothing.
"""
import sys

import certifi
import charset_normalizer
import idna
import requests
import understatapi
import urllib3
from understatapi import UnderstatClient

PLAYER_ID = "2371"  # same id as the home-network test, from the library's docstring
TIMEOUT_SECONDS = 20


def main() -> int:
    print("python", sys.version.split()[0])
    print("understatapi", understatapi.__version__)
    print("requests", requests.__version__)
    print("urllib3", urllib3.__version__)
    print("idna", idna.__version__)
    print("certifi", certifi.__version__)
    print("charset-normalizer", charset_normalizer.__version__)

    statuses = []
    client = UnderstatClient()
    client.session.hooks["response"].append(lambda res, **_: statuses.append(res.status_code))
    rows = None
    try:
        rows = client.player(PLAYER_ID).get_shot_data(timeout=TIMEOUT_SECONDS, allow_redirects=False)
    except Exception as err:  # report whatever happens, never retry
        print("error type:", type(err).__name__)
        print("http status from err.__cause__:", getattr(getattr(err.__cause__, "response", None), "status_code", None))
        # requests errors describe the connection; the library's own errors are not printed
        if isinstance(err, requests.RequestException):
            print("error detail:", str(err)[:300])
    finally:
        client.session.close()

    print("http status:", statuses[0] if statuses else None)
    print("http responses received:", len(statuses))
    print("rows returned:", "yes" if rows else "no")
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        print("shot row field names:", sorted(rows[0]))
    elif rows:
        print("unexpected rows type:", type(rows).__name__)
    return 0 if statuses == [200] and rows else 1


if __name__ == "__main__":
    sys.exit(main())
