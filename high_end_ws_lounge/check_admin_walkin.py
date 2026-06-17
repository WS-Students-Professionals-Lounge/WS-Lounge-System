import requests
from bs4 import BeautifulSoup

BASE = 'http://127.0.0.1:5000'
LOGIN = BASE + '/auth/login'
ADMIN = BASE + '/admin/dashboard'

s = requests.Session()
# get login page to get csrf token if any
r = s.get(LOGIN)
print('GET login', r.status_code)

# The login form likely uses 'email' and 'password'
payload = {'email': 'wslounge@lounge.com', 'password': 'ws12345'}
# Try to post
r = s.post(LOGIN, data=payload, allow_redirects=True)
print('POST login', r.status_code, '->', r.url)

r = s.get(ADMIN)
print('GET admin', r.status_code)

soup = BeautifulSoup(r.text, 'html.parser')
# Check for walkin modal
walkin = soup.find(id='walkinModal')
addTime = soup.find(id='addTimeModal')
scripts = [s.get('src') for s in soup.find_all('script') if s.get('src')]

print('walkin exists:', bool(walkin))
print('addTime exists:', bool(addTime))
print('script includes:')
for s in scripts:
    print(' -', s)

# Dump walkin form inputs
if walkin:
    inputs = walkin.find_all(['input','textarea','select'])
    print('walkin form inputs:')
    for i in inputs:
        print('  ', i.name, i.get('id'), i.get('name'))


print('\nFinished')
