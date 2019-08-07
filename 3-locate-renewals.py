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

renewals_matched = open("output/3-renewals-with-registrations.ndjson", "w")
renewals_not_matched = open("output/3-renewals-with-no-registrations.ndjson", "w")
has_renewal = open("output/3-registrations-with-renewal.ndjson", "w")
no_renewal = open("output/3-registrations-with-no-renewal.ndjson", "w")
potentially_foreign = open("output/3-potentially-foreign-registrations.ndjson", "w")

comparator = Comparator(
    "output/1-parsed-renewals.ndjson",
    "output/2-cross-references-in-foreign-registrations.ndjson",
)
before = time.time()
count = 0
for i in open("output/2-registrations-in-range.ndjson"):
    reg = Registration(**json.loads(i))
    if comparator.is_foreign(reg):
        output = potentially_foreign
    else:
        renewals = comparator.renewal_for(reg)
        reg.renewals = renewals
        if renewals:
            output = has_renewal
        else:
            output = no_renewal
    json.dump(reg.jsonable(), output)
    output.write("\n")
    count += 1
    if not count % 10000:
        after = time.time()
        print("%d %.2fsec" % (count, after-before))
        before = after
        after = None
    
# Now that we're done, we can write a list of all the renewals that
# had no associated registration.
for regnum, renewals in renewals_by_regnum.items():
    if regnum not in seen_regnums:
        json.dump({regnum:renewals}, renewals_not_matched)
        renewals_not_matched.write("\n")
