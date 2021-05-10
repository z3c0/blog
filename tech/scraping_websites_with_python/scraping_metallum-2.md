# Scraping Websites with Python

In the [last entry of this series](https://github.com/z3c0/blog/blob/main/tech/scraping_websites_with_python/scraping_metallum-1.md), we covered the basics of extracting data from a web page by using the website's API. In this installment, we're going to be exanding on the scripted used last time to complete the same task more quickly.

## Part 3: Networked Multithreading (using `thread` and `queue`)

### `thread`/`queue` vs `multiprocessing`

In this excercise, we're going to be utilizing the standard libraries `thread` and `queue` - however, there are times when the `multiprocessing` library is a far better choice. [Here's a good blog post on the subject](https://timber.io/blog/multiprocessing-vs-multithreading-in-python-what-you-need-to-know/) to help you understand the very large distinction between the two seemingly-similar approaches.

### Why multithread at all?

By default, Python is a single-threaded language, meaning that one can't *truly* multithread with Python as one would in one of the heftier lower-level languages. This is due to Python's [Global Interpreter Lock](https://realpython.com/python-gil/), or "GIL". In short, the GIL ensures that the Python interpreter is only able to be accessed by one thread at a time, meaning that no matter how many threads you create, they're still going to have to wait their turn to run statements against the Python interpreter. So why do it at all?

Whether or not threading is a good solution for you comes down to the problem that you're trying to solve. The problem we're solving - downloading a set of lists of varying lengths - just so happens to be a problem that is better solved with threading.

Here's a rough count of the number of records for letters A through F:

| letter    | records
|:-         |:-
| A         | 13000
| B         | 9000
| C         | 9000
| D         | 12000
| E         | 7000
| F         | 5000

Given the above list and the nature of web requests, we can make a few assertions:

- Letter A has more records than the following five letters
- A single dataset must be downloaded one page at a time
- There's a non-trivial amount of time between when a page is requested and when the page is returned

When downloading each page for letter A, instead of waiting for each page to return, you can utilize that precious time to send a web request for one of the following letters instead.

Without threading, you would have to wait for each letter to complete before moving on to the next, but when using threading, you can queue all six letters to begin downloading at (approximately) the same time. So even though we can't *truly* multi-thread with Python, we can still get a significant performance advantage by taking advantage of the gaps between web requests.

### Our script

Our complete script can be viewed [here](https://github.com/z3c0/blog/blob/main/tech/scraping_websites_with_python/scraping_metallum-2.py), which we will now walk through bit-by-bit.

#### Imports

We're going to be utilizing four native libraries (`json`, `time`, `queue`, and `threading`) alongside two third-party libraries (`requests` and `pandas`).

``` python
import json
import time
import requests
import queue as q
import pandas as pd
import threading as thr
```

If you don't have `requests` or `pandas` installed, you can do so with `pip`.

``` cmd
python -m pip install requests && python -m pip install pandas
```

#### Constants

We're putting all of our reusable static values into a `class` called `Constants`. This is to help keep our script (and global namespace) organized.

``` python

class Constants:
    ALPHABET = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L',
                'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X',
                'Y', 'Z', 'NBR', '~']
    HTTP_REQUEST_HEADERS = {'User-Agent': 'python-3.9'}
    PAGE_SIZE = 500
    CSV_HEADERS = ('band', 'country', 'genre', 'status')
    OUTPUT_FILE = 'bands.csv'
    REQUEST_ATTEMPTS = 3

```

#### Components

When creating programs that use threading, it can be difficult to manage common tasks, due to threads warring with each other over resources. Sharing resources between threads can lead to *race conditions*, where a value is changed by one thread while still being utilized by another. To ensure this doesn't happen, we can utilize the `Lock` class provided by the `threading` module.

First, we'll use a logging component that will allow our threads to print to `stdout`, or a file, if specified.

``` python

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

```

Next, we'll use a component for writing our data to an output file.

``` python

class DataComponent:
    """A component for writing data to a CSV"""

    def __init__(self, path, headers):
        open(Constants.OUTPUT_FILE, 'a').close()
        self._write_lock = thr.Lock()
        self._path = path
        self._headers = headers

    def write(self, data):
        with self._write_lock:
            df = pd.DataFrame(data, columns=self._headers)
            df.to_csv(self._path, mode='a', index=False)

```

And finally, a component for logging errors.

``` python

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

```

To make these classes globally accessible, we can instantiate them in a single entity, called `Output`.

``` python

class Output:
    log = LogComponent()
    data = DataComponent('bands.csv', ('band', 'country', 'genre', 'status'))
    error = ErrorLogComponent('metallum_errors.csv')

```

#### Functions

Next, we'll need two functions to help us perform our task. The first one is `_create_metallum_api_endpoint`, which takes a letter of the alphabet, a position in the letter's associated dataset (`offset`), and the number of records we want returned from our request (`page_size`).

The second function, `_download_bands_by_letter`, utilizes the first function to retrieve every record for a given letter. To understand how these functions work, you can review the [prior post on this topic](https://github.com/z3c0/blog/blob/main/tech/scraping_websites_with_python/scraping_metallum-1.md).

``` python

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

```

#### Threading

Now that we've established our utilities, we can move on to the primary function of our script.

``` python

def download_metal_bands(verbose=False):
    """Get every band from Encyclopaedia Metallum using the website API"""

    if not verbose:
        Output.log.disable()
    else:
        Output.log.message('beginning download')

    alphabet = [(-i, l) for i, l in enumerate(Constants.ALPHABET)]
    queue_size = int(len(alphabet) / 2)
    thread_count = int(len(alphabet) / 3)

    priority_queue = q.PriorityQueue(queue_size)
    threads = list()

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
        threads.append(thread)

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
        for _ in threads:
            priority_queue.put((0, str()))

        # empty the queue
        while not priority_queue.empty():
            _ = priority_queue.get_nowait()


```

Firstly, we need to create some important variables.

``` python

    # Assign a priority to each letter based on it's position
    # We are going to be using a PriorityQueue, which sorts entries
    # based on the given priority (a higher number is a higher priority)
    alphabet = [(-i, l) for i, l in enumerate(Constants.ALPHABET)]

    # Choose your thread count based on your computer's capabilities.
    # Too many threads will cause waiting to occur, but too little
    # threads will leave potential performance gains on the table.
    thread_count = int(len(alphabet) / 3)

    # You can make your queue any size that you want, but it's 
    # important that the thread count be less than the queue's size.
    # You don't want your threads to wait for the queue 
    # to load another value every time a thread completes its task.
    priority_queue = q.PriorityQueue(int(len(alphabet) / 2))

    # Create a list in which to store our Thread objects.
    threads = list()

```

Next, we need to create a function for our threads. This function will act as the primary code body for each thread. By declaring the function within our `download_metal_bands` function, we're ensuring the availability of the variables within our current scope - our queue, in particular.

``` python

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

```

At the beginning of the thread, we retrieve the next available value from the queue by calling the `get()` method on our `PriorityQueue` object. Once we've finished processing the value with our `_download_bands_by_letter()` function, we can signal our completion with the `task_done()` method. This will come in handy later.

Our thread function is designed so that it will continue looping over queue items until it receives an item with a priority of `0`. By using a `PriorityQueue`, we can send our exit signal to the front of the line, bypassing any values that have already been queued. This stands in contrast to the regular `Queue` object, which returns values based on the order they were added to the queue.
However, we cannot simply break upon finding a zero, as we still need to call our `task_done()` method on our `PriorityQueue` object.

Once we've created our threading function, we can instantiate our threads.

``` python

    for _ in range(thread_count):
        thread_kwargs = {'daemon': True,
                         'target': _download_bands_concurrently}

        thread = thr.Thread(**thread_kwargs)
        thread.start()
        threads.append(thread)

```

Now it's time to send values to our threads.

``` python

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
        for _ in threads:
            priority_queue.put((0, str()))

        # empty the queue
        while not priority_queue.empty():
            _ = priority_queue.get_nowait()

```

Calling the `join()` method on our `PriorityQueue` will tell our program to wait until every call of `get()` has had a corresponding call of `task_done()`. *Be very careful using `join()` - if an error in one of your threads prevents `task_done()` from being called, your program will run indefinitely. Depending on the error, you may be forced to hunt down the rogue Python process and kill it manually.*

After every item has been processed, we can clear out our threads by sending the exit signal we covered earlier. In this case, we're just sending a `tuple` with a priority of `0` coupled with an empty string.

The final step to run is emptying our queue. If everything runs smoothly, this step won't be necessary. However, in the event of an error, you'll need some way to close out your threads, or else your program will stall as your threads continue to run.