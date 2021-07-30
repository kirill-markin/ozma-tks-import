
import requests
import datetime
import json
import time

from flask import Flask, request, redirect
import waitress

from after_response import AfterResponse

from funDBAccess import FunDBClient
from tksacq import TksAcq

import logging
from pprint import pformat

import copy

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)

logger = logging.getLogger('tks-bot')

with open('config.json') as conf:
    settings = json.load(conf)

logger.setLevel(settings['Loglevel'])

def make_app():

    app = Flask(__name__)
    after_response = AfterResponse(app)

    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

    terminal = settings['Terminal']
    password = settings['Password']
    update_time = settings['UpdateTime']
    schema_name = settings['schema_name']
    view_name = settings['view_name']

    #  def update():       # местный метод для вызова обновления ключа, не используется
        #  while(True):
            #  logger.debug('Checking if token needs updating...')
            #  dbClient.update_token()
            #  time.sleep(int(update_time))

    @app.route('/pay-form', methods = ['POST'])
    def payformAsync():
        logger.debug('pay-form:')
        logger.debug(pformat(request.get_json()))

        request_data = copy.deepcopy(request.data.decode('utf-8'))
        @after_response.once
        def firstInsert():
            acquiring.firstInsert(request_data)

        return ('OK', 200)

    @app.route('/tinkoff', methods = ['POST'])
    def tinkoffAsync():
        logger.debug('tinkoff:')
        logger.debug(pformat(request.get_json()))

        request_data = copy.deepcopy(request.data.decode('utf-8'))
        @after_response.once
        def secondInsert():
            acquiring.secondInsert(request_data)

        return ('OK', 200)



#  @app.route('/')
#  def root():
    #  return ('Hello', 200)

#  @app.route('/test_ok')    # запускаем первый тест терминала тинькова, по сути, создаем платеж
                        #  # данные карты можно посмотреть в "тестирование" для терминала
#  def test_ok():
    #  return acquiring.test_ok()

#  @app.route('/test_insuf')
#  def test_insuf():
    #  return acquiring.test_insufficient()

#  @app.route('/test_receipt')
#  def test_receipt():
    #  return acquiring.test_receipt()

#  @app.route('/test_data')
#  def test_data():
    #  return acquiring.test_data()


#  @app.route('/resend')   # по этой штуке я пытался дернуть тиньковский Resend, но в итоге ничего так и не получил на /requests
                        #  # возможно, тиньков переотсылает только по какому-нибудь timeout error, по 400-ошибкам и по 500-ошибкам он не отсылал повторно
#  def resend():
    #  return acquiring.resend()


#  @app.route('/requests', methods = ['POST']) # сюда нам приходят тиньковские нотификации, настраивается в "нотификациях" в настройках магазина
#  def onRequest():
    #  return acquiring.requrl(request)



# тут соединение с озмой и начало рефреша токена доступа к озме
    dbClient = FunDBClient(settings)

    dbClient.start_session()
    dbClient.check_auth()

    acquiring = TksAcq(dbClient, settings)

#dbClient.edit_entry(view_name, schema_name, 333242967, {'amount': 5000})

#updater = threading.Thread(target=update, args=())
#updater.start()

# запуск сервера, чтобы получать нотификации
#app.run(host='0.0.0.0', port='80')
    waitress.serve(app, host='0.0.0.0', port='80')


app = make_app()
app.run(port=80)