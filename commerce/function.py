import datetime
import json


def stoday() -> str:
    return datetime.date.today().strftime("%Y-%m-%d")


def sdates_between(first_date: str, last_date: str) -> list:
    begin = datetime.datetime.strptime(first_date, "%Y-%m-%d")
    end = datetime.datetime.strptime(last_date, "%Y-%m-%d")
    return [(begin + datetime.timedelta(days=x)).strftime("%Y-%m-%d")
            for x in range(0, (end - begin).days + 1)]


def sdates_next_from(first_date: str, delta_days: int) -> list:
    begin = datetime.datetime.strptime(first_date, "%Y-%m-%d")
    return [(begin + datetime.timedelta(days=x)).strftime("%Y-%m-%d")
            for x in range(0, delta_days)]


def sdates_lasts_till(last_date: str, delta_days: int) -> list:
    end = datetime.datetime.strptime(last_date, "%Y-%m-%d")
    begin = end - datetime.timedelta(days=(delta_days - 1))
    return [(begin + datetime.timedelta(days=x)).strftime("%Y-%m-%d")
            for x in range(0, delta_days)]


def sdates_lasts_till_yesterday(delta_days: int) -> list:
    begin = datetime.date.today() - datetime.timedelta(days=delta_days)
    return [(begin + datetime.timedelta(days=x)).strftime("%Y-%m-%d")
            for x in range(0, delta_days)]


def sdates_lasts_till_today(delta_days: int) -> list:
    begin = datetime.date.today() - datetime.timedelta(days=(delta_days - 1))
    return [(begin + datetime.timedelta(days=x)).strftime("%Y-%m-%d")
            for x in range(0, delta_days)]


def sdates_lasts_till_yesterday_rev(delta_days: int) -> list:
    end = datetime.date.today()
    return [(end + datetime.timedelta(days=x)).strftime("%Y-%m-%d")
            for x in range(-1, -delta_days - 1, -1)]


def format_dash_to_point(sdate):  # 2020-06-03
    return '.'.join([sdate[8:10], sdate[5:7], sdate[:4]])


def is_testing_order(func):
    def wrapper(order, *args, **kwargs):
        if order['test']:
            text = ('Это недействительный заказ (дубль или тест)!\n'
                    '--------------------------------------------\n\n')
        else:
            text = ''
        return text + func(order, *args, **kwargs)
    return wrapper


def append_unique_ids(source, update):
    source_ids = [item['id'] for item in source]
    for item in update:
        if item['id'] not in source_ids:
            source_ids.append(item['id'])
            source.append(item)


def upto(number, part):
    remainder = number % part
    if remainder:
        return number - remainder + part
    return number


def get_paid_time(time):
    hours, seconds = divmod(time, 3600)
    minutes = upto(seconds, 60) // 60
    minutes = upto(minutes, 15)
    return f'{hours} ч {minutes} м'


def get_last_month_range(date):
    last_month = date.month - (1 if date.month != 1 else -11)
    start = date.replace(month=last_month, day=1)
    end = date.replace(day=1) - datetime.timedelta(1)
    return start, end


def text_order_arrival(order):
    if order['destinations'] and 'arrival_time' in order['destinations'][0]:
        arrival = order['destinations'][0]['arrival_time']
        arrival = datetime.datetime.strptime(arrival[:19], '%Y-%m-%dT%H:%M:%S')
        arrival_date = arrival.date()

        if arrival_date == datetime.date.today():
            arrival_dtext = 'сегодня'
        elif arrival_date == (
            datetime.date.today() + datetime.timedelta(days=1)):
            arrival_dtext = 'завтра'
        else:
            arrival_dtext = arrival.strftime('%d.%m')
            
        arrival_ttext = arrival.strftime('%H:%M')
        
        return f'{arrival_dtext} в {arrival_ttext}'
    return 'ближайшее время'


def text_order_id(order):
    return f'{order["id"]} на {text_order_arrival(order)}'


def text_order_cost(order):
    tariff_type = order['calculation']['transport_tariff']['extension']['type']

    if tariff_type == 'by_distance':
        cost_type = 'фиксированная'
        case = ' за перевозку (включая 4 часа погрузки и разгрузки на адресах)'
    elif tariff_type == 'first':
        cost_type = 'расчётная'
        time = get_paid_time(order['time_at_way'])
        case = f' за {time}'
    else:
        cost_type = 'специальная'
        case = ''
    cost = order['total_cost']

    return f'{cost_type} стоимость {cost} руб{case}'


def text_order_cost_cap(order):
    return text_order_cost(order).capitalize() + '.'


def text_order_tariff(order):
    tariff = order['extra_search_params']['tariff_tier']['name']
    loaders = order.setdefault('loaders', 'special')
    if loaders:
        if loaders == 1:
            loaders_text = '1 грузчик'
        elif loaders == 2:
            loaders_text = '2 грузчика'
        else:
            loaders_text = 'особые условия погрузки/разгрузки'
        loaders_text += ' (водитель может выступать в роли грузчика)'
    else:
        loaders_text = 'без грузчиков'
    
    options = text_order_options(order)
    if options:
        options = ':\n' + options
    return f'Тариф {tariff}, {loaders_text}{options}.'


def text_order_options(order):
    options = []
    if order['calculation']['services']:
        description = {
            'lifting': 'спуск/подъём',
            'assembly': 'разборка/сборка',
        }
        for service in order['calculation']['services']:
            options.append('- ' + description[service])
    if order['entry_ttk']:
        options.append('- нужен пропуск в ТТК')
    return ';\n'.join(options)


def text_order_addresses(order):
    addresses = []
    for destination in order['destinations']:
        addresses.append('- ' + destination['destination']['addr'])
    return 'Адреса:\n' + ';\n'.join(addresses) + '.'


def text_order_contact(order):
    company = ''
    if 'company_client' in order['client']:
        company = '(' + order['client']['company_client']['name'] + ')'

    contact = [
        order['client'].setdefault('name', ''),
        order['client'].setdefault('patronymic', ''),
        order['client'].setdefault('surname', ''),
        '+' + order['client']['phone'],
        company,
    ]
    return ' '.join([e for e in contact if e])


@is_testing_order
def text_cost_notice(order):
    notice = f'По заказу {text_order_id(order)} {text_order_cost(order)}.'

    try:
        t_tariff = (order['calculation']['transport_tariff']
                    ['extension']['tariff'])

        # int минут продление
        extra_time = t_tariff['additional_period_tariffication']

        # int рублей за продление
        extra_cost = t_tariff['additional_period_price']

    except KeyError:
        t_tariff = 'Специальный'
        extra_time = 0
        extra_cost = 0
    if 'loaders_tariff' in order['calculation'].keys():
        l_tariff = (json.loads(
            order['calculation']['loaders_tariff']
            ['extension']['tariff']
        ))

        # int рублей за продление погрузки
        extra_cost += l_tariff['additional_period_price']
    if extra_time:
        tariff_type = (order['calculation']['transport_tariff']
                       ['extension']['type'])
        if tariff_type == 'by_distance':
            notice += (' Если на всех адресах в сумме потребуется более 4 ч - '
                       f'доплата по {extra_cost} р'
                       f' за каждые дополнительные {extra_time} мин.')
        elif tariff_type == 'first':
            notice += (f' Если потребуется доп. время - по {extra_cost} р'
                       f' за каждые {extra_time} мин.')
    
    if ('taxi_search' in order
        and order['taxi_search']['status'] == 'accepted'):
        notice += ('\n\nЭкипаж свяжется с Вами перед выездом на первый адрес.')
    else:
        notice += ('\n\nКак только экипаж будет подобран - Вы получите'
                   ' сообщение с номером телефона водителя. Экипаж свяжется с'
                   ' Вами перед выездом на первый адрес.')
    return notice


@is_testing_order
def text_order_advt(order):
    info = [
        f'Заказ {text_order_id(order)}.',
        text_order_cost_cap(order),
        text_order_tariff(order),
        text_order_addresses(order),
        order['comment'],
        'Чтобы принять заказ, откройте приложение MOVER Водитель.'
        ' (Если заказ не отображается - напишите нам в личные сообщения.)'
    ]
    
    return '\n\n'.join([e for e in info if e])


@is_testing_order
def text_order_info(order):
    info = [
        f'Заказ {text_order_id(order)}.',
        text_order_cost_cap(order),
        text_order_tariff(order),
        text_order_addresses(order),
        order['comment'],
        text_order_contact(order),
    ]
    
    return '\n'.join([e for e in info if e])