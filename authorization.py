import requests

from bs4 import BeautifulSoup

from credentials import LOGIN_PASSWORD, LOGIN_USERNAME, HEADERS, VILLAGE_URL


def logged_in_session():
    session = requests.Session()
    session.headers = HEADERS
    html = session.get(VILLAGE_URL).text
    resp_parser = BeautifulSoup(html, 'html.parser')
    login_value = resp_parser.find('input', {'name': 'login'})['value']

    data = {
        'name': LOGIN_USERNAME,
        'password': LOGIN_PASSWORD,
        's1': 'Přihlásit+se',
        'w': '',
        'login': login_value
    }

    session.post('https://ts3.czsk.travian.com/login.php', data=data)

    return session
