# Tinkoff acquiring to Ozma import bot
## Installation
Packages needed:
- Flask
- waitress (production WSGI server)

That's basically it, everything else is in Python 3.7.0 already I think.
## Configuration
Use config.json to configure your bot:
| Key           | Value | Comment |
|-----          |------|---|
| Terminal      | Terminal name to watch out for, provided by Tinkoff |
| Password  | Password for the said terminal |
| address   | API base address for Ozma instance |
| username  | Username for Ozma instance |
| password  | Password for said username |Yeah, yeah, I know, using "Password" and "password" is jank. Gonna need to change that. |
| client_id | Client ID for the bot in Ozma | Usually "tinkoffozmabot" |
| client_secret | Client secret | Usually "b9e5f47a-bc97-4146-abe1-048d95d396d5" |
| schema_name | Schema name for the transaction table in ozma |
| view_name | Transaction table view name |
## Running
Just run main.py file with python. That will start a publicly accessible Flask server. It needs to be accessable from the outside, obviously, so the acquiring can POST stuff to it.

Remember to put in your address, from which this server will be accessible from the outside, into Tinkoff acquiring, so the acquiring actually knows where it should POST updates to.
## Current functions
Currently service responds to two requests, `/pay-form` and `/tinkoff`.
First one happens right after form sending by user and before payment, so there are some basic information, who and what paying for.
This data sends to Ozma after little reformatting.
Second, `/tinkoff`, happens several times and have some status changes from Tinkoff API,
in easiest success case it's two requests with `AUTHORIZED` and `CONFIRMED` statuses, order not guaranteed.
Afer receiving this request service tries to find order with same `OrderId` and updates it's data.

`/pay-form` body example:
```python
{'Amount': 100,
 'DATA': {'Email': 'example@example.com',
          'Name': 'Noname Noname',
          'Phone': '+7(000)000-00-00'},
 'Description': 'Тест',
 'OrderId': 2505,
 'Receipt': {'Email': 'example@example.com',
             'EmailCompany': 'info@info.info',
             'Items': [{'Amount': 100,
                        'Name': 'Тест',
                        'PaymentMethod': 'full_payment',
                        'PaymentObject': 'service',
                        'Price': 100,
                        'Quantity': 1,
                        'Tax': 'none'}],
             'Phone': '+7(000)000-00-00',
             'Taxation': 'usn_income'},
 'TerminalKey': '0123456789'}
```

`/tinkoff` body example:
```python
{'Amount': 100,
 'CardId': 0123456,
 'ErrorCode': '0',
 'ExpDate': '01234',
 'OrderId': '1234',
 'Pan': '0123456******654321',
 'PaymentId': 123456,
 'Status': 'CONFIRMED',
 'Success': True,
 'TerminalKey': '0123456789',
 'Token': '4a7353b7ba5344b323aa8da67c9a17ae305bd827e115fcf2c2209fa00c73188d'}
```

## What's next
- Check for data validity from Tinkoff
- Configure Flask properly
- Possibly manual .csv import for inputting older entries

# How to

Restart service
```
git pull &&
sudo ./quick_ubuntu_20_lts_startup.sh 
```
