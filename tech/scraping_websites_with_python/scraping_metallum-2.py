import sys
import json
import requests
import pandas as pd
import threading as thr
import multiprocessing as mp

from queue import PriorityQueue

ALPHABET = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
            'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
            'NBR', '~']


AVAILABLE_CPUS = mp.cpu_count()


REQUEST_HEADERS = {'User-Agent': 'python-3.9'}
PAGE_SIZE = 500
CSV_HEADERS = ('band', 'country', 'genre', 'status')

OUTPUT_FILE = 'bands.csv'


def _create_metallum_api_endpoint(letter, offset, page_size):
    """Returns an API endpoint for retrieving a segment of bands
    beginnging with the given letter"""

    endpoint = f'browse/ajax-letter/l/{letter}/json'
    query_string = f'sEcho=1&iDisplayStart={offset}&iDisplayLength={page_size}'

    return f'https://www.metal-archives.com/{endpoint}?{query_string}'


def download_metal_bands():
    """Get every band from Encyclopaedia Metallum using the website API"""

    keep_threading = True

    def _download_records_for_letter(letter):
        offset = 0
        total_records = None
        band_records = []

        while keep_threading:
            try:
                letter_endpoint = \
                    _create_metallum_api_endpoint(letter, offset, PAGE_SIZE)
                letter_page = \
                    requests.get(letter_endpoint, headers=REQUEST_HEADERS)

                if letter_page.status_code != 200:
                    error_text = \
                        f'{letter_page.status_code}: {letter_page.text[:500]}'
                    raise Exception(error_text)

                json_data = json.loads(letter_page.text)
                band_records += json_data['aaData']

                if offset == 0:
                    total_records = json_data['iTotalRecords']

                offset += PAGE_SIZE

                if offset <= total_records:
                    continue
            except Exception as err:
                while priority_queue.get():
                    priority_queue.task_done()
                print(err)

            break

        bands_df = pd.DataFrame(band_records, columns=CSV_HEADERS)
        bands_df.to_csv(OUTPUT_FILE, mode='a', index=False)

        print('csv updated')

    def _download_bands_concurrently():
        while keep_threading:
            queued_letter = priority_queue.get()
            if queued_letter != -1 and keep_threading:
                _download_records_for_letter(queued_letter)

            priority_queue.task_done()

    priority_queue = PriorityQueue(AVAILABLE_CPUS * 2)

    for _ in range(AVAILABLE_CPUS):
        thread = thr.Thread(daemon=True, target=_download_bands_concurrently)
        thread.start()

    # truncate our output file
    open(OUTPUT_FILE, 'w').close()

    try:
        for letter in ALPHABET:
            priority_queue.put(letter)

        priority_queue.join()
    except KeyboardInterrupt:
        pass
    except Exception as err:
        print(err)

    keep_threading = False
    for _ in range(thr.active_count()):
        priority_queue.put(-1)

    priority_queue.join()
    sys.exit(0)


if __name__ == '__main__':
    download_metal_bands()
