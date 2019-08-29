import unicodecsv 
from pdb import set_trace
from model import Registration
import json
import sys
if len(sys.argv) > 1:
    cutoff = float(sys.argv[1])
else:
    cutoff = 0.8

output = open("output/ia-2-matches-%s.tsv" % cutoff, "wb")
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
for i in open("output/ia-1-matched.ndjson"):
    data = json.loads(i)
    quality = data['quality']
    if quality < cutoff:
        continue
    
    ia = data['ia']
    cce = Registration(**data['cce'])

    ia_id = "https://archive.org/details/" + ia['identifier']
    cce_id = cce.uuid

    ia_title = ia['title']
    cce_title = cce.title
    
    ia_author = ia.get('creator') or ia.get('creatorSorter') or ""
    if isinstance(ia_author, list):
        ia_author = "; ".join(ia_author)
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

    ia_year = ia['year']
    cce_year = cce.best_guess_registration_date.year

    disposition = cce.disposition

    ia_row = ["", ia_title, ia_author, ia_year, ia_id, quality, ""]
    cce_row = ["", cce_title, cce_author, cce_year, cce_id, "", disposition]
    packages.append(Package(ia_row, cce_row))

for package in sorted(packages, key=lambda x: x.sort_key):    
    package.write(out)
