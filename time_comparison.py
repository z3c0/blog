
import timeit
import pandas as pd

first_version_name = 'tech.scraping_websites_with_python.scraping_metallum-1'
second_version_name = 'tech.scraping_websites_with_python.scraping_metallum-2'

first_version = __import__(first_version_name, fromlist=[''])
second_version = __import__(second_version_name, fromlist=[''])

single_thread_func = first_version.download_metal_bands
multi_thread_func = second_version.download_metal_bands

timers = [('single', timeit.Timer(single_thread_func)),
          ('multi', timeit.Timer(multi_thread_func))]

timers = [(v, t.timeit(number=5) / 60) for v, t in timers]

columns = ('version', 'minutes')
timers_df = pd.DataFrame(timers, columns=columns)

print(timers_df)
