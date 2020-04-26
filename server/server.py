### Конфиг
import os

# Tак как путь пробрасывается в докер контейнер по хардкорженому значению,
# мы можем обращаться к статичной директории внутри контейнера
WATCH_PATH = '/watchpath/'  # os.environ.get('WATCH_PATH')

# if not WATCH_PATH:
#    raise ValueError('WATCH_PATH missing!')
# WATCH_PATH = os.path.join(WATCH_PATH, '')  # Добавляем trailing slash для унификации

WATCH_PATH_LEN = len(WATCH_PATH)

AMQP_URL = os.environ.get('AMQP_URL')

if not AMQP_URL:
    raise ValueError('AMQP_URL missing!')


###

# Шорткат для получения всех файлов в директории. Полезно при первом старте.
def get_full_directory():
    return os.listdir(WATCH_PATH)


### Обработка отправляемых данных

def sanitize_path(path):
    # Отрезаем полный путь и берем только изменившийся файл/директорию.
    return path[WATCH_PATH_LEN:]


###

### RabbitMQ
import pika
import ujson as json  # Должно слегка ускорить работу

connection = pika.BlockingConnection(
    pika.URLParameters(AMQP_URL)
)

main_channel = connection.channel()
main_channel.exchange_declare(exchange='dirdata', exchange_type='fanout')


def send_message(event, path):
    body = json.dumps({'event': event, 'file': path})  # file может быть и директорией
    print(body)
    main_channel.basic_publish(
        body=body,
        exchange='dirdata',
        routing_key=''
    )


###

### Watchdog класс для ивентов в системе

# from watchdog.observers import Observer
# К сожалению, для проброшенных в докер контейнер директорий, механизм нотификаций не уведомляет об изменениях.
# Пришлось использовать поллинг обсервер, это может сказаться на скорости :(
# "Баг" описан тут: https://github.com/gorakhargosh/watchdog/issues/283#issuecomment-61079649

from watchdog.observers.polling import PollingObserver as Observer
from watchdog.events import FileSystemEventHandler


class MyHandler(FileSystemEventHandler):
    # Переименование
    def on_moved(self, event):
        send_message('REPLACE', [sanitize_path(event.src_path), sanitize_path(event.dest_path)])

    # Создание
    def on_created(self, event):
        send_message('ADD', sanitize_path(event.src_path))

    # Удаление/перенос из папки
    def on_deleted(self, event):
        send_message('DELETE', sanitize_path(event.src_path))


###


### Хэндлер для обработки новых клиентов, чтобы выслать им список содержимого в директории
from threading import Thread

handler_connection = pika.BlockingConnection(pika.URLParameters(AMQP_URL))
handler_channel = handler_connection.channel()
handler_channel.queue_declare(queue='initdirdata')


def process_init_data(msg):
    try:
        data = msg.decode('utf-8')
    except (ValueError, TypeError):
        print('Error processing incoming data')
        return

    if data == 'INIT':
        send_message('INIT', get_full_directory())


def callback(ch, method, properties, body):
    process_init_data(body)


# Для простоты используется auto_ack=True
handler_channel.basic_consume('initdirdata', callback, auto_ack=True)


def start_consuming():
    print('Starting init server...')
    handler_channel.start_consuming()


T = Thread(target=start_consuming)

###

if __name__ == "__main__":
    print('Running server ...')
    T.daemon = True
    T.start()

    event_handler = MyHandler()
    observer = Observer()

    # recursive = True позволит отслеживать sub-директории,
    # но для них придется переписать хэндлер, т.к. modified event триггерится и на поддиректории.
    observer.schedule(event_handler, path=WATCH_PATH, recursive=False)
    observer.start()

    try:
        while True:
            pass  # Или time.sleep(n)
    except KeyboardInterrupt:
        print('Stopping server...')
        observer.stop()
    observer.join()

    connection.close()
