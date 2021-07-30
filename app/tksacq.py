import logging
import requests
import hashlib
import json
import datetime

logger = logging.getLogger('tks-bot')
logger.setLevel(logging.DEBUG)
from pprint import pformat

class TksAcq:
    def __init__(self, dbClient, settings):
        self.terminal = settings['Terminal']
        self.password = settings['Password']
        self.update_time = settings['UpdateTime']
        self.schema_name = settings['schema_name']
        self.view_name = settings['view_name']
        self.dbClient = dbClient

    def reformatDataFirst(self, data):
        newData = {
            'tks_date_time': str(datetime.datetime.now(tz=datetime.timezone.utc)),
            'tks_amount': data['Amount'],
            'tks_order_id': data['OrderId'],
            'is_deleted': False,
            'tks_state': 'Ожидается оплата',
            'tks_shop': data['TerminalKey'],
            'tks_description': data['Description'],
            'tks_phone': data['DATA']['Phone'],
            'tks_email': data['DATA']['Email'],
            'tks_customer_name': data['DATA']['Name']
        }
        logger.debug('Rerformat-1 from ' + str(data) + ' to ' + str(newData))
        return newData

    def reformatDataSecond(self, data):
        newData = {
            'tks_date_time': str(datetime.datetime.now(tz=datetime.timezone.utc)),
            'tks_order_id': data['OrderId'],
            'tks_state': data['Status']
        }
        logger.debug('Rerformat-2 from ' + str(data) + ' to ' + str(newData))
        return newData


    # Вставка данных после оформления заявки, до оплаты.
    def firstInsert(self, request_data):
        self.logRequest(request_data)
        try:
            data = json.loads(request_data)
            response = self.addEntry(data)
        except (KeyError, json.decoder.JSONDecodeError) as e:
            logger.error('No valid data in request!')
            logger.debug(e)
            return('400 BAD REQUEST', 400)
        return ('OK', 200)


    # Вставка данных после оплаты.
    def secondInsert(self, request_data):
        self.logRequest(request_data)
        try:
            data = json.loads(request_data)
            if self.checkToken(data):
                logger.info('Token match, calling editEntry.')
                response = self.editEntry(data)
            else:
                logger.error('Token mismatch! Not paying attention.')
        except (KeyError, json.decoder.JSONDecodeError) as e:
            logger.error('No valid data in request!')
            logger.debug(e)
            return('400 BAD REQUEST', 400)
        return ('OK', 200)


    def addEntry(self, data): # переформатировать инфо от поступившего поста и отправить в озму
        logger.info('Adding entry ' + str(data))
        self.dbClient.update_token() # чиним токен на всякий

        new_data = self.reformatDataFirst(data)
        response = self.dbClient.add_entry(self.view_name, self.schema_name, new_data)
        try:
            logger.debug((
                "-----ozma response\n", 
                response.json(),
                "\n-----\n"
            ))
        except:
            pass

        return response


    def editEntry(self, data): # найти по tks-id запись и поменять ее
        logger.info('Editing entry ' + str(data))
        self.dbClient.update_token() # чиним токен на всякий

        view = self.dbClient.get_view('tinkoff_shop_import', self.schema_name)
        #  logger.debug('view:\n' + pformat(view))

        new_data = self.reformatDataSecond(data)

        order_id = str(data['OrderId'])

        rows = self.get_modified_rows(view)
        # По идее, тут не нужен массив, максимум найдётся один элемент, но раньше было так и я оставил.
        id_matches = [row['mainId'] for row in rows
                      if row['values']['tks_order_id']['value'] == order_id
                         and not row['values']['is_deleted']['value']]
        if id_matches:
            logger.info('Found ' + str(len(id_matches)) + ' matches, updating them all...')
            for match in id_matches:
                response = self.dbClient.edit_entry(self.view_name, self.schema_name, int(match), new_data)
                try:
                    logger.debug((
                        "-----ozma response\n", 
                        response.json(),
                        "\n-----\n"
                    ))  
                except:
                    pass
                return response
        else:
            logger.info('No match found for order_id ' + str(order_id) + ' !')
            #  logger.debug(order_id)
            #  logger.debug(pformat(rows))



    # Преобразовывает записи, чтобы значения в строках были словарём, а не массивом.
    def get_modified_rows(self, view):
        rows = view['result']['rows']
        columns = view[ 'info']['columns']
        keys = list(map(lambda x: x['name'], columns))
        modify_values = lambda row: {keys[i]: value for i, value in enumerate(row['values'])}
        entities = [{**row, 'values': modify_values(row)} for row in rows]
        return entities


    def logRequest(self, request_data):
        logger.info('Got POST!:\n------\nrequest_data:\n'+str(request_data)+'\n------')



    #  def test_ok(self):
        #  url = "https://securepay.tinkoff.ru/v2/Init"
        #  items = {
            #  'TerminalKey'   : self.terminal,
            #  'OrderId'       : 'test ' + str(datetime.datetime.now()),
            #  'Amount'        : '1339',
            #  'Description'   : 'ok transaction',
        #  }
        #  items = self.addTokenToDict(items)
        #  logger.debug('Sending ' + str(items) + ' to Tinkoff')
        #  r = requests.post(url, json = items)
        #  logger.debug('Got ' + str(r.json()) + ' from Tinkoff')
        #  return redirect(r.json()['PaymentURL'])

    #  def test_insufficient(self):
        #  url = "https://securepay.tinkoff.ru/v2/Init"
        #  items = {
            #  'TerminalKey'   : self.terminal,
            #  'Password'      : self.password,
            #  'OrderId'       : 'This will fail',
            #  'Amount'        : '1339',
            #  'Description'   : 'insufficient funds',
        #  }
        #  items = self.addTokenToDict(items)
        #  r = requests.post(url, json = items)
        #  return redirect(r.json()['PaymentURL'])

    #  def test_receipt(self):
        #  url = "https://securepay.tinkoff.ru/v2/Init"
        #  receipt = {
            #  'Phone'         : '+79099242236',
            #  'Taxation'      : 'osn'
        #  }
        #  items = {
            #  'TerminalKey'   : self.terminal,
            #  'Password'      : self.password,
            #  'OrderId'       : str(datetime.datetime.now()),
            #  'Amount'        : '1339',
            #  'Description'   : 'receipt',
            #  'Receipt'       : receipt
        #  }
        #  items = self.addTokenToDict(items)
        #  r = requests.post(url, json = items)
        #  return redirect(r.json()['PaymentURL'])

    #  def test_data(self):
        #  url = "https://securepay.tinkoff.ru/v2/Init"
        #  data = {
            #  'TestData'      :"uhhhhh"
        #  }
        #  items = {
            #  'TerminalKey'   : self.terminal,
            #  'Password'      : self.password,
            #  'OrderId'       : str(datetime.datetime.now()),
            #  'Amount'        : '1339',
            #  'Description'   : 'data',
            #  'DATA'       : data
        #  }
        #  items = self.addTokenToDict(items)
        #  r = requests.post(url, json = items)
        #  return redirect(r.json()['PaymentURL'])

    #  def resend(self):
        #  url = "https://securepay.tinkoff.ru/v2/Resend"
        #  items = {
            #  'TerminalKey'   : self.terminal,
            #  'Password'      : self.password
        #  }
        #  items = self.addTokenToDict(items)
        #  r = requests.post(url, json=items)
        #  return str(r.json())

    #  def requrl(self, request):
        #  self.logRequest(request)
        #  try:
            #  data = json.loads(request.data.decode('utf-8'))
            #  if self.checkToken(data):
                #  logger.info('Token match, calling editEntry.')
                #  self.editEntry(data)
            #  else:
                #  logger.error('Token mismatch! Not paying attention.')
        #  except (KeyError, json.decoder.JSONDecodeError) as e:
            #  logger.error('No valid data in request!')
            #  logger.debug(e)
            #  return('400 BAD REQUEST', 400)
        #  return ('OK', 200)

    #  def formToken(self, requestDict):  # хитрая схема типа-контрольной-суммы типа-проверки-пароля. Почитать можно в документации api эквайринга
        #  items = sorted(requestDict.items())
        #  itemValues = [x[1] for x in items]
        #  itemValuesString = ''.join(itemValues)
        #  token = hashlib.sha256(itemValuesString.encode('utf-8'))
        #  return token.hexdigest()

    #  def addTokenToDict(self, requestDict):
        #  passwordDict = requestDict.copy()
        #  passwordDict['Password']=self.password
        #  token = self.formToken(passwordDict)
        #  requestDict['Token']=token
        #  logger.debug('passwordDict is ' + str(passwordDict))
        #  logger.debug('requestDict is ' + str(requestDict))
        #  return requestDict

    def checkToken(self, requestDict):
        logger.debug('Checking token for ' + str(requestDict))
        checkDict = requestDict.copy()
        del checkDict['Token']

        checkDict['Password'] = self.password
        items = sorted(checkDict.items())
        itemValues = [str(x[1]) for x in items]
        itemValuesString = ''.join(itemValues)
        token = hashlib.sha256(itemValuesString.encode('utf-8'))
        hexToken = token.hexdigest()

        logger.debug('Source     token: ' + str(requestDict['Token']))
        logger.debug('Calculated token: ' + str(hexToken))

        # TODO FIXME !!!: fix this
        #  return True if hexToken == requestDict['Token'] else False
        return True
