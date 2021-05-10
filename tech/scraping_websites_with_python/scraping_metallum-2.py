import json
import time
import requests
import queue as q
import pandas as pd
import threading as thr


class Constants:
    ALPHABET = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L',
                'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X',
                'Y', 'Z', 'NBR', '~']
    PAGE_SIZE = 500
    REQUEST_ATTEMPTS = 3


class LogComponent:
    """A class for logging info to stdout or a specified file"""

    def __init__(self, stdout=True, path=None):
        if not stdout and path is None:
            print('[-]:\ta path is required when stdout is False')
            stdout = True

        if stdout:
            self._write_func = print
        else:
            open(path, 'w').close()

            def _print_wrapper(*values, sep=' ', end='\n'):
                with open(path, 'a') as log_file:
                    print(*values, sep=sep, end=end, file=log_file)

            self._write_func = _print_wrapper

        self.msg_number = 0
        self._is_enabled = True
        self._print_lock = thr.Lock()

    def message(self, text):
        if self._is_enabled:
            with self._print_lock:
                self.msg_number += 1
                self._write_func(f'[{self.msg_number}]:\t{text}')

    def disable(self):
        self._is_enabled = False


class DataComponent:
    """A component for writing data to a CSV"""

    def __init__(self, path, headers):
        open(path, 'a').close()
        self._write_lock = thr.Lock()
        self._path = path
        self._headers = headers

    def write(self, data):
        with self._write_lock:
            df = pd.DataFrame(data, columns=self._headers)
            df.to_csv(self._path, mode='a', index=False)


class ErrorLogComponent:
    """A component for writing errors to a CSV"""
    def __init__(self, path):
        open(path, 'w').close()

        self._write_lock = thr.Lock()
        self._path = path

    def write(self, data):
        with self._write_lock:
            df = pd.DataFrame(data)
            df.to_csv(self._path, mode='a', index=False, header=False)


class Output:
    log = LogComponent()
    data = DataComponent('bands.csv', ('band', 'country', 'genre', 'status'))
    error = ErrorLogComponent('metallum_errors.csv')


def _create_metallum_api_endpoint(letter, offset, page_size):
    """Returns an API endpoint for retrieving a segment of bands
    beginnging with the given letter"""

    endpoint = f'browse/ajax-letter/l/{letter}/json'
    query_string = f'sEcho=1&iDisplayStart={offset}&iDisplayLength={page_size}'

    return f'https://www.metal-archives.com/{endpoint}?{query_string}'


def _download_bands_by_letter(letter):
    """download every band for a given letter"""
    offset = -1 * Constants.PAGE_SIZE
    total_records = -1
    page_attempts = 0
    band_records = []
    parse_errors = []

    while offset <= total_records:
        if page_attempts == 0:
            offset += Constants.PAGE_SIZE
        elif page_attempts == Constants.REQUEST_ATTEMPTS:
            record_range = f'{offset} - {offset + Constants.PAGE_SIZE}'
            Output.log.message((f'{letter} failed to download records '
                                f'{record_range}'))

            # give up and go to the next page
            offset += Constants.PAGE_SIZE

        letter_endpoint = \
            _create_metallum_api_endpoint(letter, offset, Constants.PAGE_SIZE)
        letter_page = requests.get(letter_endpoint,
                                   headers={'User-Agent': 'python-3.9'})

        if letter_page.status_code == 520:
            # give the web server a few seconds to catch its breath
            time.sleep(10)
            page_attempts += 1
            continue

        elif letter_page.status_code not in (200, 403):
            error = (f'{letter}:{offset} {letter_page.status_code}'
                     f' error encountered (attempt {page_attempts + 1})')
            Output.log.message(error)

        try:
            json_data = json.loads(letter_page.text)
            band_records += json_data['aaData']
            total_records = json_data['iTotalRecords']
            page_attempts = 0

        except json.decoder.JSONDecodeError:
            # log error and store for investigation
            if page_attempts == Constants.REQUEST_ATTEMPTS - 1:
                Output.log.message(f'{letter}:{offset} JSON error encountered')

                scrubbed_text = letter_page.text.replace('\n', '')
                scrubbed_text = scrubbed_text.replace('\t', '')
                parse_errors.append({'letter': letter,
                                     'endpoint': letter_endpoint,
                                     'response_code': letter_page.status_code,
                                     'reponse_text': scrubbed_text})

            page_attempts += 1
            continue

    if total_records != -1:
        Output.log.message((f'{letter} complete '
                           f'({total_records} records)'))
        Output.data.write(band_records)
    else:
        Output.log.message((f'{letter} failed to download'))

    Output.error.write(parse_errors)


def download_metal_bands(verbose=False):
    """Get every band from Encyclopaedia Metallum using the website API"""

    if not verbose:
        Output.log.disable()
    else:
        Output.log.message('beginning download')

    alphabet = [(-i, l) for i, l in enumerate(Constants.ALPHABET)]
    thread_count = int(len(alphabet) / 3)
    priority_queue = q.PriorityQueue(int(len(alphabet) / 2))

    def _download_bands_concurrently():
        keep_threading = True
        while keep_threading:
            try:
                priority, queued_letter = priority_queue.get()

                if priority == 0:
                    keep_threading = False
                else:
                    _download_bands_by_letter(queued_letter)
            except Exception as e:
                keep_threading = False
                Output.log.message(str(e))
            finally:
                priority_queue.task_done()

    for _ in range(thread_count):
        thread_kwargs = {'daemon': True,
                         'target': _download_bands_concurrently}

        thread = thr.Thread(**thread_kwargs)
        thread.start()

    try:
        for letter in alphabet:
            priority_queue.put(letter)

        priority_queue.join()
    except KeyboardInterrupt:
        Output.log.message('keyboard interrupt detected')
    except Exception as err:
        Output.log.message(err.text)
    finally:
        Output.log.message('sending close signal to threads')
        for _ in range(thread_count):
            priority_queue.put((0, str()))

        # empty the queue
        while not priority_queue.empty():
            _ = priority_queue.get_nowait()


if __name__ == '__main__':
    download_metal_bands(verbose=True)
