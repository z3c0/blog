import os
import sys
import json
import time
import requests
import pandas as pd

import threading as thr
import queue as q


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


def _download_bands_by_letter(letter):
    """download every band for a given letter"""
    offset = 0
    total_records = 1
    band_records = []
    errors = []

    # log.message(f'downloading letter {letter}')

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
                error_text = \
                    f'{letter_page.status_code}: {letter_page.text[:500]}'
                raise Exception(error_text)

            try:
                json_data = json.loads(letter_page.text)
                band_records += json_data['aaData']

            except json.decoder.JSONDecodeError:
                errors.append({'response_code': letter_page.status_code,
                               'reponse_text': letter_page.text})
                json_data is None

            if offset == 0:
                if json_data is not None:
                    total_records = json_data['iTotalRecords']
                else:
                    # set total_records to just beyond the next offset to keep
                    # the process moving to the next page in the event of an error
                    total_records = min(10000, offset + PAGE_SIZE + 1)

            offset += PAGE_SIZE

            if offset <= total_records:
                continue

            break

        error_log.write(errors)

    except Exception as err:
        log.message(err)

    log.message(f'letter {letter} complete ({total_records} records)')
    csv.write(band_records)


def download_metal_bands(verbose=False):
    """Get every band from Encyclopaedia Metallum using the website API"""

    if not verbose:
        log.disable()

    def _download_bands_concurrently():
        thread = thr.current_thread().name
        # log.message(f'entering {thread}')
        keep_threading = True
        while keep_threading:
            queued_letter = priority_queue.get()

            if queued_letter != -1:
                _download_bands_by_letter(queued_letter)
            else:
                keep_threading = False
                # log.message(f'closing {thread}')

            priority_queue.task_done()

    priority_queue = q.PriorityQueue(AVAILABLE_CPUS * 2)
    threads = list()

    for n in range(AVAILABLE_CPUS):
        thread_kwargs = {'daemon': True,
                         'target': _download_bands_concurrently,
                         'name': f'thr_{n}'}

        thread = thr.Thread(**thread_kwargs)
        thread.start()
        threads.append(thread)

    # truncate our output file
    open(OUTPUT_FILE, 'w').close()

    try:
        for letter in ALPHABET:
            priority_queue.put(letter)

        priority_queue.join()
    except KeyboardInterrupt:
        pass
    except Exception as err:
        log.message(err)

    # send close signal to threads
    for _ in threads:
        priority_queue.put(-1)
    priority_queue.join()


if __name__ == '__main__':
    download_metal_bands(verbose=True)
