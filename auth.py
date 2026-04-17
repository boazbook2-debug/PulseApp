import requests
from urllib.parse import urlencode
from secrets import get_secret

OURA_AUTH_URL = "https://cloud.ouraring.com/oauth/authorize"
OURA_TOKEN_URL = "https://api.ouraring.com/oauth/token"
OURA_PERSONAL_INFO_URL = "https://api.ouraring.com/v2/usercollection/personal_info"
SCOPES = "email personal daily heartrate session tag spo2 ring_configuration workout stress"


def _redirect_uri():
    return get_secret("STREAMLIT_URL", "http://localhost:8501")


def get_auth_url():
    client_id = get_secret("OURA_CLIENT_ID")
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": _redirect_uri(),
        "scope": SCOPES,
        "prompt": "consent",
    }
    return f"{OURA_AUTH_URL}?{urlencode(params)}"


def exchange_code_for_tokens(code):
    client_id = get_secret("OURA_CLIENT_ID")
    client_secret = get_secret("OURA_CLIENT_SECRET")
    response = requests.post(
        OURA_TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _redirect_uri(),
        },
        auth=(client_id, client_secret),
    )
    response.raise_for_status()
    return response.json()


def get_user_info(access_token):
    response = requests.get(
        OURA_PERSONAL_INFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
    )
    response.raise_for_status()
    return response.json()
