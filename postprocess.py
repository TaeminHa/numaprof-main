import re
import statistics
from collections import OrderedDict, defaultdict
import pandas as pd

timelist = defaultdict(list, OrderedDict())
stats = defaultdict(list, OrderedDict())
idx = 0

with open('results.txt') as results:
    for line in results:
        if "# of remote" in line:
            timelist[idx % 50].append(float(re.search(r"\d+\.\d+", line).group()))
            idx += 1

# print(timelist)
print()

for k,v in timelist.items():
    stats[k] = [min(v), max(v), statistics.median(v), statistics.mean(v), statistics.stdev(v)]

# print(stats)

df = pd.DataFrame.from_dict(stats, orient='index', columns=['min', 'max', 'median', 'mean', 'std_dev'])
print(df)
