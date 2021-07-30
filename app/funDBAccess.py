import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import datetime
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import LegacyApplicationClient

import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
from pprint import pformat

logger = logging.getLogger('tks-bot')
logger.setLevel(logging.DEBUG)

# Обёртка для повтора запроса несколько раз при неудаче.
# На основе https://www.peterbe.com/plog/best-practice-with-retries-with-requests
def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 503, 504),
    method_whitelist=['GET', 'POST'],
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        method_whitelist=method_whitelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


class FunDBClient:
    def __init__(self, settings):
        self.client_id = settings['client_id']
        self.client_secret = settings['client_secret']
        self.base_url = settings['address']
        self.authorize_url = 'https://account.ozma.io/auth/realms/default/protocol/openid-connect/token'
        self.check_url = '/check_access'

        self.username = settings['username']
        self.password = settings['password']

    def update_token(self): # получаем токен заново
        current_time = datetime.datetime.now().replace(microsecond=0).timestamp()
        time_left = int(self.saved_token['expires_at']) - int(current_time)
        logger.debug('Updating token expiry time to '+str(time_left))
        self.saved_token['expires_in'] = str(time_left)
        if time_left <= 20:
            logger.info('Refreshing token.')
            self.start_session()

    def start_session(self): # получаем токен сначала
        self.oauth = OAuth2Session(client=LegacyApplicationClient(client_id=self.client_id))
        self.saved_token = self.oauth.fetch_token(token_url=self.authorize_url,
                username=self.username, password=self.password, client_id=self.client_id,
                client_secret=self.client_secret)
        return self.saved_token

    def check_auth(self): # проверка токена
        headers = {'Authorization': 'Bearer ' + self.saved_token['access_token'], 'token_type': self.saved_token['token_type']}
        url = self.base_url + self.check_url
        request = requests_retry_session().get(url=url, headers=headers)
        response = request.status_code
        if response == 200:
            logger.info('Auth check passed.')
            return True
        else:
            logger.info('Got '+str(response)+' when checking access.')
            return False

    def get(self, url, params={}): # обертка для GET на озму
        headers = {'Authorization': 'Bearer ' + self.saved_token['access_token'], 'token_type': self.saved_token['token_type']}
        request_url = self.base_url + url

        logger.info('GET '+ request_url + ('' if params=={} else (' with params '+str(params))))

        request = requests_retry_session().get(url=request_url, headers=headers, params=params)

        logger.info('Got ' + str(request.status_code))
        if request.status_code==200:
            try:
                response = request.json()
                logger.info('Got JSON from response')
                return response
            except ValueError:
                logger.error('Could not get JSON from response.')
                return None
        else:
            logger.error('Not a 200, aborting.')
            return None

    def get_view(self, view_name, schema_name, params={}): # обертка, чтобы получить сразу вьюху
        url = '/views/by_name/'+schema_name+'/'+view_name+'/entries'
        return self.get(url=url, params=params)

    # Шлём сообщение об ошибке в лог Озмы.
    def post_log(self, message):
        entityRef = {'schema': 'user', 'name': 'service_logs'}
        entry = {
            'datetime_str': str(datetime.datetime.now(tz=datetime.timezone.utc)),
            'info': message
        }
        operation = {'type': 'insert', 'entity': entityRef, 'entries': entry}
        transaction = {'operations': [operation]}

        self.post(url='/transaction', body=json.dumps(transaction), is_logging=True)

    def post(self, url, body, is_logging=False): # обертка для поста на озму
        headers = {'Authorization': 'Bearer ' + self.saved_token['access_token'], 'token_type': self.saved_token['token_type'],
                    'Content-type': 'application/json'}
        request_url = self.base_url + url

        logger.info('POST '+ request_url + ('' if body=={} else (' with body '+str(body))))

        request = requests_retry_session().post(url=request_url, headers=headers, data=body)

        logger.info('Got ' + str(request.status_code) + ' ' + str(request.text))
        if request.status_code==200:
            try:
                response = request.json()
                logger.info('Got JSON from response')
                return response
            except ValueError:
                logger.error('Got 200, but could not get JSON from response.')
                return None
        else:
            logger.error('Not a 200, aborting.')

            # Костыльная проверка, чтобы при ошибке при попытке логгирования оно не ушло в цикл.
            if not is_logging:
                self.post_log('Error: ' + str(request.status_code) + ', ' + str(request.text))

            return request

    def add_entry(self, table_name, schema_name, entry): # обертка для добавления записи
        entityRef = {'schema':schema_name, 'name':table_name}
        operation = {'type':'insert', 'entity':entityRef, 'entries':entry}
        transaction = {'operations':[operation]}

        url = '/transaction'
        #  self.post_log('test test test')

        return self.post(url=url, body=json.dumps(transaction))

    def edit_entry(self, table_name, schema_name, id, entry):
        entityRef = {'schema':schema_name, 'name':table_name}
        operation = {'type':'update', 'entity':entityRef, 'id':id, 'entries':entry}
        transaction = {'operations':[operation]}

        url = '/transaction'

        return self.post(url=url, body=json.dumps(transaction))
