import os
from json import JSONDecodeError
import ujson as json
import pika

AMQP_URL = os.environ.get('AMQP_URL')

if not AMQP_URL:
    raise ValueError('AMQP_URL missing!')

connection = pika.BlockingConnection(pika.URLParameters(AMQP_URL))
channel = connection.channel()
channel.exchange_declare(exchange='dirdata', exchange_type='fanout')

result = channel.queue_declare(queue='', exclusive=True)
queue_name = result.method.queue
channel.queue_bind(exchange='dirdata', queue=result.method.queue)

# Список файлов в директории, Псевдо-хранилище данных, пришедших от брокера.
LOCAL_DATA = []


# Рендер списка файлов "влоб"
def print_data():
    print('--- Directory contents ---')
    print("\n".join(LOCAL_DATA))
    print('--------------------------')


def process_data(msg):
    global LOCAL_DATA
    try:
        data = json.loads(msg.decode('utf-8'))
    except (TypeError, JSONDecodeError):
        print('Error processing incoming data')
        return

    if data['event'] == 'ADD':
        if data['file'] not in LOCAL_DATA:
            LOCAL_DATA.append(data['file'])
            LOCAL_DATA.sort()  # Например, сортировка по имени.

    elif data['event'] == 'DELETE':
        if data['file'] in LOCAL_DATA:
            LOCAL_DATA.remove(data['file'])

    elif data['event'] == 'REPLACE':
        # Убираем старый файл
        if data['file'][0] in LOCAL_DATA:
            LOCAL_DATA.remove(data['file'][0])

        # Добавляем в список новый
        if data['file'][1] not in LOCAL_DATA:
            LOCAL_DATA.append(data['file'][1])
            LOCAL_DATA.sort()

    elif data['event'] == 'INIT':
        data['file'].sort()

        if LOCAL_DATA == data['file']:
            return

        LOCAL_DATA = data['file']

    print_data()


def callback(ch, method, properties, body):
    process_data(body)


# Для простоты используется auto_ack=True
channel.basic_consume(queue=queue_name, on_message_callback=callback, auto_ack=True)

print('Starting client...')

channel.basic_publish(
    body='INIT',
    exchange='',
    routing_key='initdirdata',
)

try:
    channel.start_consuming()
except KeyboardInterrupt:
    print('Stopping client..')
    connection.close()
