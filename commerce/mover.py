import urllib.request
import urllib.parse
import json
import datetime
import configparser
import time

import jsbeautifier

import function


class Session:
    def __init__(self, username=None, password=None, logfile=None):
        self.api_url = 'https://api.mover24.ru'

        self.logfile=logfile
        if not logfile:
            self.logfile = '../var/log/session.txt'

        config = configparser.ConfigParser()
        config.read('../config/working.ini')

        self.username = username
        if not username:
            self.username = config.get('MOVER', 'username')
        self.password = password
        if not password:
            self.password = config.get('MOVER', 'password')
            
        self.token = None
        self.logon()
    
    def log(self, record):
        with open(self.logfile, 'a+') as logfile:
            logfile.write(f'{datetime.datetime.now()}: {record}\n')

    def request(self, resource, method='GET', data=None):
        url = self.api_url + resource
        if data:
            data = urllib.parse.urlencode(data).encode()
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header('User-Agent', 'mailto:imsmastermsk@gmail.com')
        req.add_header('cookie', f'token={self.token}')
        self.log(url)
        response = urllib.request.urlopen(req)
        body = response.read().decode('utf-8')
        return json.loads(body)

    def get(self, resource, data=None):
        return self.request(resource, method='GET', data=data)

    def post(self, resource, data=None):
        return self.request(resource, method='POST', data=data)

    def put(self, resource, data=None):
        return self.request(resource, method='PUT', data=data)

    def delete(self, resource, data=None):
        return self.request(resource, method='DELETE', data=data)

    def logon(self):
        token_response = self.get('/token')
        if token_response['success']:
            self.token = token_response['token']
        else:
            raise
        data = {'username': self.username, 'password': self.password}
        auth_response = self.post('/login/device.json', data=data)
        if not auth_response['success']:
            raise
    
    def get_account(self, username=None):
        if username:
            url = f'/me/user.json?name={username}'
        else:
            url = '/me.json'
        response = self.get(url)
        if response['success']:
            return response['account']
        raise

    def get_order(self, id_):
        url = f'/support/me/orders/drafts/{id_}.json'
        response = self.get(url)
        if response['success']:
            return response['draft']
        raise
    
    def get_orders_page(self, offset=None, params=None):
        url = '/support/me/orders/drafts.json'
        if offset or params:
            if not params:
                params = dict()
            if offset:
                params['offset'] = offset
            url = url + '?' + urllib.parse.urlencode(params)
        response = self.get(url)
        if response['success']:
            return response['drafts']
        raise

    def get_orders(self, params=None, max_items=100, overlap=3):
        page = self.get_orders_page(params=params)
        if params and ('period[start]' in params.keys()
                       or 'period[end]' in params.keys()):
            return page
        items = page
        while page and 29 < len(items) < max_items:
            offset = len(items) - overlap
            page = self.get_orders_page(offset=offset, params=params)
            function.append_unique_ids(items, page)
        return items[:max_items]

    def get_contract(self, id_):
        url = f'/support/me/orders/{id_}.json'
        response = self.get(url)
        if response['success']:
            return response['order']
        raise

    def get_contracts_page(self, offset=None, params=None):
        url = '/freighter/all/orders.json'
        if offset or params:
            if not params:
                params = dict()
            if offset:
                params['offset'] = offset
            url = url + '?' + urllib.parse.urlencode(params)
        response = self.get(url)
        if response['success']:
            return response['orders']
        raise

    def get_contracts(self, params=None, max_items=100, overlap=3):
        page = None
        timeout = 1
        while page is None:
            try:
                page = self.get_contracts_page(params=params)
            except urllib.error.HTTPError as e:
                if e.code == 500:
                    time.sleep(timeout)
                    timeout *= 2
                else:
                    raise e

        if 'period[start]' in params.keys() or 'period[end]' in params.keys():
            return page
        contracts = page
        while page and 19 < len(contracts) < max_items:
            offset = len(contracts) - overlap
            page = self.get_contracts_page(offset=offset, params=params)
            function.append_unique_ids(contracts, page)
        return contracts[:max_items]

    def download_image(self, url):
        req = urllib.request.Request(url)
        req.add_header('cookie', f'token={self.token}')
        response = urllib.request.urlopen(req)
        return response.read()

    def get_items(self, resource, items_name):
        response = self.request(resource)
        if not isinstance(response[items_name], list):
            return response[items_name]
        
        items = {item['id']: item for item in response[items_name]}
        received_count = len(response[items_name])
        while response[items_name]:
            params = {'offset': received_count}
            url = resource + '?' + urllib.parse.urlencode(params)
            response = self.request(url)
            items.update({item['id']: item for item in response[items_name]})
            received_count += len(response[items_name])
        
        new_items_count = received_count - len(items)
        received_count = 0
        while new_items_count > 0:
            params = {'offset': received_count}
            url = resource + '?' + urllib.parse.urlencode(params)
            response = self.request(url)
            items.update({item['id']: item for item in response[items_name]})
            new_items_count -= len(response[items_name])
            received_count += len(response[items_name])

        return sorted(items.values(), key=lambda item: item['id'], reverse=True)
