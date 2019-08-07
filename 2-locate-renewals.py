# Handle works that were clearly renewed, works that clearly were
# not, and works that were referenced by a foreign registration.
#
# One-to-one regnum match: work was clearly renewed.
# No regnum match, no children: work was clearly not renewed.
# Multiple regnum matches: it's complicated, handle it later.
# Mentioned in foreign registration: assume this work, too is a foreign publication.
#
# Also eliminate from consideration renewals that do not correspond to
# any registration in the dataset. (They're probably renewals for
# some other piece of the dataset.)
from pdb import set_trace
from collections import defaultdict
import json
import time
from compare import Comparator
from model import Registration

class Processor(object):

    def __init__(self, comparator, output, cross_references):
        self.comparator = comparator
        self.output = output
        self.cross_references = cross_references

    def process(self, registration):
        renewals = self.comparator.renewal_for(registration)
        registration.renewals = renewals
        json.dump(registration.jsonable(require_disposition=True), self.output)
        self.output.write("\n")
        if registration.is_foreign:
            # This looks like a foreign registration. We'll filter it out
            # in the next step, but we need to record its cross-references
            # now, so we can filter _those_ out in the next step.
            for xref in registration.parse_xrefs():
                out = self.cross_references
                json.dump(xref.jsonable(), out)
                out.write("\n")

        # Handle children as totally independent registrations. Note
        # that in the next step we may disquality children because the
        # parent registration was disqualified based on more complete
        # information.
        for child in registration.children:
            child = Registration(**child)
            child.parent = registration
            self.process(child)

annotated = open("output/2-registrations-with-renewals.ndjson", "w")
cross_references = open("output/2-cross-references-in-foreign-registrations.ndjson", "w")

comparator = Comparator("output/1-parsed-renewals.ndjson")
processor = Processor(comparator, annotated, cross_references)
before = time.time()
count = 0
for i in open("output/0-parsed-registrations.ndjson"):
    processor.process(Registration(**json.loads(i)))
    count += 1
    if not count % 10000:
        after = time.time()
        print("%d %.2fsec" % (count, after-before))
        before = after
        after = None

# Now that we're done, we can divide up the renewals by whether or not
# we found a registration for them.

# TODO: This is still misclassifying registrations that were matched,
# e.g. "A417695"
renewals_matched = open("output/2-renewals-with-registrations.ndjson", "w")
renewals_not_matched = open("output/2-renewals-with-no-registrations.ndjson", "w")
for regnum, renewals in comparator.renewals.items():
    for renewal in renewals:
        if renewal in comparator.used_renewals:
            out = renewals_not_matched
        else:
            out = renewals_matched
        json.dump(renewal.jsonable(), out)
        out.write("\n")
