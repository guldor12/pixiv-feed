from base64 import urlsafe_b64encode
from hashlib import sha256
from pprint import pprint
from secrets import token_urlsafe
from sys import exit
from textwrap import dedent
from urllib.parse import urlencode
import webbrowser

import requests

# Latest app version can be found using GET /v1/application-info/android
USER_AGENT = "PixivAndroidApp/5.0.234 (Android 11; Pixel 5)"
REDIRECT_URI = "https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback"
LOGIN_URL = "https://app-api.pixiv.net/web/v1/login"
AUTH_TOKEN_URL = "https://oauth.secure.pixiv.net/auth/token"
CLIENT_ID = "MOBrBDS8blbauoSck0ZfDbtuzpyT"
CLIENT_SECRET = "lsACyCD94FhDUtGTXi3QzcFE2uU1hqtDaKeqrdwj"


def s256(data):
    """S256 transformation method."""

    return urlsafe_b64encode(sha256(data).digest()).rstrip(b"=").decode("ascii")


def oauth_pkce(transform):
    """Proof Key for Code Exchange by OAuth Public Clients (RFC7636)."""

    code_verifier = token_urlsafe(32)
    code_challenge = transform(code_verifier.encode("ascii"))

    return code_verifier, code_challenge


def login():
    code_verifier, code_challenge = oauth_pkce(s256)
    login_params = {
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "client": "pixiv-android",
    }

    webbrowser.open(f"{LOGIN_URL}?{urlencode(login_params)}")

    print(
        dedent(
            """
            Instructions:
            1. In the page just opened in your web browser, open dev console (F12) and switch to network tab.

            2. Enable persistent logging ("Preserve log").

            3. Type into the filter field: callback?

            4. Proceed with Pixiv login.

            5. After logging in you should see a blank page and request that looks like this:

               https://app-api.pixiv.net/web/v1/users/auth/pixiv/callback?state=...&code=....

               Copy value of the code param into the pixiv_auth.py's prompt and hit the Enter key.

            WARNING:
            The lifetime of code is extremely short, so make sure to minimize delay
            between step 5 and 6. Otherwise, repeat everything starting step 1.

            If you did everything right and Pixiv did not change their auth flow,
            the necessary API tokens should be saved to the database.
            """
        ).strip(),
        end="\n\n",
    )

    try:
        code = input("code: ").strip()
    except (EOFError, KeyboardInterrupt):
        return

    response = requests.post(
        AUTH_TOKEN_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "code_verifier": code_verifier,
            "grant_type": "authorization_code",
            "include_policy": "true",
            "redirect_uri": REDIRECT_URI,
        },
        headers={"User-Agent": USER_AGENT},
    )

    data = response.json()

    if "access_token" in data and "refresh_token" in data:
        return data

    print("error:")
    pprint(data)
    exit(1)
