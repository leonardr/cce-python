# * All registrations for works published abroad are filtered out of the main
#   list.
#
# * But we save in a separate dataset all references to _other_ works
#   found in those works. Those _other_ works may themselves have been
#   published abroad -- we'll have to check on the next pass.

from pdb import set_trace
import json
import datetime
import re
from collections import Counter
from model import Registration
import time

class Processor(object):

    # Before this year, everything published in the US is public
    # domain.
    CUTOFF_YEAR = datetime.datetime.utcnow().year - 95

    def __init__(self):
        self.foreign = open("output/2-registrations-foreign.ndjson", "w")
        self.too_old = open("output/2-registrations-before-%s.ndjson" % self.CUTOFF_YEAR, "w")
        self.too_new = open("output/2-registrations-after-1963.ndjson", "w")
        self.in_range = open("output/2-registrations-in-range.ndjson", "w")
        self.errors = open("output/2-registrations-error.ndjson", "w")
        self.cross_references_in_foreign_registrations = open(
            "output/2-cross-references-in-foreign-registrations.ndjson", "w"
        )
        #self.cross_references_from_renewals = json.load(open(
        #    "output/1-renewal-cross-references.json"
        #))
    
    def disposition(self, registration):
        if registration.is_foreign:
            # We have good evidence that this is a foreign
            # registration.
            registration.disposition = "Foreign publication."
            return self.foreign

        if not registration.regnums:
            return self.error(
                registration, "No registration number."
            )

        reg_date = registration.best_guess_registration_date
        if not reg_date:
            return self.error(
                registration, "No registration or publication date."
            )
        if reg_date.year < self.CUTOFF_YEAR:
            registration.disposition == 'Published before cutoff year.'
            return self.too_old
        elif reg_date.year > 1963:
            registration.disposition == 'Published after cutoff  year.'
            return self.too_new
        else:
            return self.in_range

    def process(self, data):
        registration = Registration.from_json(data)
        output = self.disposition(registration)
        if output == self.foreign:
            for xref in registration.parse_xrefs():
                out = self.cross_references_in_foreign_registrations
                json.dump(xref.jsonable(), out)
                out.write("\n")
        json.dump(registration.jsonable(), output)
        output.write("\n")

        # In general, children are totally independent
        # registrations. However, if the 'parent' registration (the
        # one for which the most data is available) is deemed to be
        # out of range, there's a good chance the 'children' are also
        # out of range.
        for child in registration.children:
            child = Registration(**child)
            child_output = self.disposition(child)
            child.parent = registration
            if child_output == self.in_range and output != self.in_range:
                child.disposition = "Classified with parent."
                child.warnings.append(
                    "This registration seems like a good candidate, but it was associated with a registration which was deemed not to be a candidate. To be safe, this registration will be put in the same category as its 'parent'; it should be checked manually."
                )
                child_output = output
            json.dump(child.jsonable(), child_output)
            child_output.write("\n")

    def error(self, registration, error):
        registration.error = error
        return self.errors

processor = Processor()
before = time.time()
count = 0
for i in open("output/0-parsed-registrations.ndjson"):
    data = json.loads(i)
    processor.process(data)
    count += 1
    if not count % 10000:
        after = time.time()
        print("%d %.2fsec" % (count, after-before))
        before = after
        after = None
        
