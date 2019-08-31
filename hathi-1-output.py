import unicodecsv 
from pdb import set_trace
from model import Registration
from collections import Counter
import json
import sys
if len(sys.argv) > 1:
    cutoff = float(sys.argv[1])
else:
    cutoff = 0.2

counter = Counter()

output = open("output/hathi-1-matches-%s.tsv" % cutoff, "wb")
out = unicodecsv.writer(output, dialect="excel-tab", encoding="utf-8")

csv_row_labels = 'decision title author year id match_quality disposition'.split()
out.writerow(csv_row_labels)

class Package(object):

    def __init__(self, ia_data, cce_data):
        self.ia_data = ia_data
        self.cce_data = cce_data

    @property
    def sort_key(self):
        return -self.ia_data[5], self.cce_data[1]

    def write(self, out):
        out.writerow(self.ia_data)
        out.writerow(self.cce_data)
        out.writerow([])

packages = []
for i in open("output/hathi-0-matched.ndjson"):
    data = json.loads(i)
    quality = data['quality']
    if quality < cutoff:
        continue

    quality = round(quality,2)

    hathi = data['hathi']
    cce = Registration(**data['cce'])

    hathi_link = "https://catalog.hathitrust.org/Record/%s" % hathi['identifier']
    cce_id = cce.uuid

    hathi_title = hathi['title']
    cce_title = cce.title

    hathi_author = hathi.get('author')
    cce_authors = cce.authors or []
    for pub in cce.publishers:
        claimants = pub.get('claimants')
        if claimants:
            for i in claimants:
                if i:
                    cce_authors.append(i)
    for pub in cce.publishers:
        nonclaimants = pub.get('nonclaimants')
        if nonclaimants:
            for i in nonclaimants:
                if i:
                    cce_authors.append(i)
    cce_author = "; ".join(cce_authors)

    hathi_year = hathi['year']
    cce_year = cce.best_guess_registration_date.year

    disposition = cce.disposition

    hathi_row = ["", hathi_title, hathi_author, hathi_year, hathi_link, quality, ""]
    cce_row = ["", cce_title, cce_author, cce_year, cce_id, "", disposition]
    packages.append(Package(hathi_row, cce_row))
    counter[quality] += 1

for package in sorted(packages, key=lambda x: x.sort_key):    
    package.write(out)

print("Number of possible matches by quality score:")
for quality, num in sorted(counter.items(), key=lambda x: -x[0]):
    print(" %s: %s" % (quality, num))
print("Total: %s" % sum(counter.values()))
