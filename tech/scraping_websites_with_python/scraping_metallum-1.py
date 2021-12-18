import time
import json
import requests
import pandas as pd

ALPHABET = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M',
            'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z',
            'NBR', '~']


def _create_metallum_api_endpoint(letter, offset, page_size):
    """Returns an API endpoint for retrieving a segment of bands
    beginnging with the given letter"""

    endpoint = f'browse/ajax-letter/l/{letter}/json'
    query_string = f'sEcho=1&iDisplayStart={offset}&iDisplayLength={page_size}'

    return f'https://www.metal-archives.com/{endpoint}?{query_string}'


def download_metal_bands():
    """Get every band from Encyclopaedia Metallum using the website API"""

    headers = {'User-Agent': 'python-3.9'}
    page_size = 500
    csv_headers = ('band', 'country', 'genre', 'status')

    open('bands.csv', 'w').close()
    open('metallum_errors.csv', 'w').close()

    for letter in ALPHABET:
        offset = 0
        total_records = 1
        band_records = []
        errors = []

        while True:
            letter_endpoint = \
                _create_metallum_api_endpoint(letter, offset, page_size)
            letter_page = requests.get(letter_endpoint, headers=headers)

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
                json_data = None

            if offset == 0:
                if json_data is not None:
                    total_records = json_data['iTotalRecords']
                else:
                    # set total_records to just beyond the next offset to keep
                    # the process moving to the next page after an error
                    total_records = min(10000, offset + page_size + 1)

            offset += page_size

            if offset <= total_records:
                continue

            break

        bands_df = pd.DataFrame(band_records, columns=csv_headers)
        bands_df.to_csv('bands.csv', mode='a', index=False)

        errors_df = pd.DataFrame(errors)
        errors_df.to_csv('metallum_errors.csv', mode='a', index=False)


if __name__ == '__main__':
    download_metal_bands()
