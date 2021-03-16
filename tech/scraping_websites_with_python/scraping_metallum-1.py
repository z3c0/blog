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

    for letter in ALPHABET:
        offset = 0
        total_records = None
        band_records = []

        while True:
            letter_endpoint = \
                _create_metallum_api_endpoint(letter, offset, page_size)
            letter_page = requests.get(letter_endpoint, headers=headers)

            if letter_page.status_code != 200:
                error_text = \
                    f'{letter_page.status_code}: {letter_page.text[:500]}'
                raise Exception(error_text)

            json_data = json.loads(letter_page.text)
            band_records += json_data['aaData']

            if offset == 0:
                total_records = json_data['iTotalRecords']

            offset += page_size

            if offset <= total_records:
                continue

            break

        bands_df = pd.DataFrame(band_records, columns=csv_headers)
        bands_df.to_csv('bands.csv', mode='a', index=False)


if __name__ == '__main__':
    download_metal_bands()
