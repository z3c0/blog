
import timeit
import pandas as pd

first_version_name = 'tech.scraping_websites_with_python.scraping_metallum-1'
second_version_name = 'tech.scraping_websites_with_python.scraping_metallum-2'

first_version = __import__(first_version_name, fromlist=[''])
second_version = __import__(second_version_name, fromlist=[''])

timers = [('single', timeit.Timer(first_version.download_metal_bands)),
         ('multi', timeit.Timer(second_version.download_metal_bands))]

timers = [(v, t.timeit(number=10) / 60) for v, t in timers]

timers_df = pd.DataFrame(timers, columns=('version', 'seconds'))
print(timers_df)
