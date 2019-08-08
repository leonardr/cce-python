import json
from pdb import set_trace
from model import Registration, Renewal
import unicodecsv 
class Spreadsheet(object):

    def __init__(self, output):
        self.out = unicodecsv.writer(
            open(output, "w"), dialect="excel-tab",
            encoding="utf-8"
        )

    def convert(self, input_file):
        self.out.writerow(Registration.csv_row_labels + Renewal.csv_row_labels)
        for line in open(input_file):
            registration = Registration.from_json(json.loads(line))
            self.out.writerow(registration.csv_row)

spreadsheets = {
    "renewed" : ["renewed", "probably-renewed", "possibly-renewed"],
    "not-renewed": ["not-renewed"],
    "foreign": ["foreign"],
}

for name, inputs in spreadsheets.items():
    output = "output/FINAL-%s.tsv" % name
    spreadsheet = Spreadsheet(output)
    for i in inputs:
        filename = "output/FINAL-%s.ndjson" % i
        spreadsheet.convert(filename)
