import os
import json
import time
import requests
import queue as q
import pandas as pd
import threading as thr


# our constants
ALPHABET = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
            'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
            'NBR', '~']
AVAILABLE_CPUS = os.cpu_count()
REQUEST_HEADERS = {'User-Agent': 'python-3.9'}
PAGE_SIZE = 500
CSV_HEADERS = ('band', 'country', 'genre', 'status')
OUTPUT_FILE = 'bands.csv'


# some utilities
class Log:
    """A class for logging info to stdout from multiple threads"""

    def __init__(self):
        self.msg_number = 0
        self._is_enabled = True
        self._print_lock = thr.Lock()

    def message(self, text):
        if self._is_enabled:
            with self._print_lock:
                self.msg_number += 1
                print(f'[{self.msg_number}]:\t{text}')

    def disable(self):
        self._is_enabled = False


class CSV:
    """A class for writing data to a CSV from multiple threads"""

    def __init__(self, path, headers):
        open(path, 'w').close()
        self._write_lock = thr.Lock()
        self._path = path
        self._headers = headers

    def write(self, data):
        with self._write_lock:
            df = pd.DataFrame(data, columns=self._headers)
            df.to_csv(self._path, mode='a', index=False)


class ErrorLog:
    def __init__(self, path):
        open(path, 'w').close()
        self._write_lock = thr.Lock()
        self._path = path

    def write(self, data):
        with self._write_lock:
            df = pd.DataFrame(data)
            df.to_csv(self._path, mode='a', index=False)


log = Log()
csv = CSV(OUTPUT_FILE, CSV_HEADERS)
error_log = ErrorLog('metallum_errors.csv')


def _create_metallum_api_endpoint(letter, offset, page_size):
    """Returns an API endpoint for retrieving a segment of bands
    beginnging with the given letter"""

    endpoint = f'browse/ajax-letter/l/{letter}/json'
    query_string = f'sEcho=1&iDisplayStart={offset}&iDisplayLength={page_size}'

    return f'https://www.metal-archives.com/{endpoint}?{query_string}'


def _get_band_count_per_letter(letter, attempt=0):
    """return the number of records per a given letter"""

    letter_endpoint = _create_metallum_api_endpoint(letter, 0, 1)
    letter_page = requests.get(letter_endpoint, headers=REQUEST_HEADERS)

    try:
        json_page = json.loads(letter_page.text)
        total_records = json_page['iTotalRecords']

    except json.decoder.JSONDecodeError:
        if attempt == 2:
            return -1  # give up

        time.sleep(10)
        total_records = _get_band_count_per_letter(letter, attempt + 1)

    return total_records


def _download_bands_by_letter(letter, total_records):
    """download every band for a given letter"""
    offset = 0
    band_records = []
    parse_errors = []

    try:
        while offset <= total_records:
            letter_endpoint = \
                _create_metallum_api_endpoint(letter, offset, PAGE_SIZE)
            letter_page = \
                requests.get(letter_endpoint, headers=REQUEST_HEADERS)

            if letter_page.status_code == 520:
                time.sleep(10)
                continue

            elif letter_page.status_code not in (200, 403):
                error = (f'{letter}:{offset} {letter_page.status_code}'
                         f' error encountered')
                log.message(error)

            try:
                json_data = json.loads(letter_page.text)
                band_records += json_data['aaData']

            except json.decoder.JSONDecodeError:
                parse_errors.append({'response_code': letter_page.status_code,
                                     'reponse_text': letter_page.text})

            offset += PAGE_SIZE

            if offset <= total_records:
                continue

            break

        error_log.write(parse_errors)

    except Exception as err:
        log.message(err)

    log.message(f'letter {letter} complete ({total_records} records)')
    csv.write(band_records)


def download_metal_bands(sort_letters=True, verbose=False):
    """Get every band from Encyclopaedia Metallum using the website API"""

    if not verbose:
        log.disable()

    if sort_letters:
        log.message('retrieving record counts')
        alphabet = [(_get_band_count_per_letter(ltr), ltr) for ltr in ALPHABET]
    else:
        alphabet = list(enumerate(ALPHABET))

    def _download_bands_concurrently():
        keep_threading = True
        while keep_threading:
            total_records, queued_letter = priority_queue.get()

            if queued_letter is not None:
                _download_bands_by_letter(queued_letter, total_records)
            else:
                keep_threading = False

            priority_queue.task_done()

    priority_queue = q.PriorityQueue(AVAILABLE_CPUS * 3)
    threads = list()

    for _ in range(AVAILABLE_CPUS):
        thread_kwargs = {'daemon': True,
                         'target': _download_bands_concurrently}

        thread = thr.Thread(**thread_kwargs)
        thread.start()
        threads.append(thread)

    # truncate our output file
    open(OUTPUT_FILE, 'w').close()

    try:
        for letter in alphabet:
            priority_queue.put(letter)

        priority_queue.join()
    except KeyboardInterrupt:
        pass
    except Exception as err:
        log.message(err.text)

    # send close signal to threads
    for _ in threads:
        priority_queue.put((-1, None))
    priority_queue.join()


if __name__ == '__main__':
    download_metal_bands(verbose=True)
