# Handle works that were clearly renewed and works that clearly were
# not.
#
# One-to-one regnum match: work was clearly renewed.
# No regnum match, no children: work was clearly not renewed.
# Multiple regnum matches: it's complicated, handle it later.
#
# Also eliminate from consideration renewals that do not correspond to
# any registration in the dataset. (They're probably renewals for
# some other piece of the dataset.)
from pdb import set_trace
from collections import defaultdict
import json

renewals_by_regnum = defaultdict(list)
seen_regnums = set()

renewals_matched = open("output/3-renewals-with-registrations.ndjson", "w")
renewals_not_matched = open(
    "output/3-renewals-with-no-registrations.ndjson", "w"
)
renewals_not_yet_matched = open(
    "output/3-renewals-not-yet-matched.ndjson", "w"
)
matched = open("output/3-registrations-with-renewal.ndjson", "w")
not_matched = open("output/3-registrations-with-no-renewal.ndjson", "w")
not_yet_matched = open("output/3-registrations-to-check.ndjson", "w")

for i in open("output/1-parsed-renewals.ndjson"):
    data = json.loads(i)
    renewals_by_regnum[data['regnum']].append(data)

for i in open("output/2-registrations-in-range.ndjson"):
    data = json.loads(i)
    num = data['regnum']
    seen_regnums.add(num)
    renewals = renewals_by_regnum[num]
    children = data['children']
    if not renewals:
        # No renewal.
        registration_output = not_matched
        renewal_output = None
        if children:
            disposition = 'Not renewed, but has children.'
        else:
            disposition = "Not renewed."       
    elif len(renewals) == 1:
        # One renewal -- this work was definitely renewed.
        renewal = renewals[0]
        registration_output = matched
        renewal_output = renewals_matched
        if renewal['reg_date'] == data['reg_date']:
            disposition = 'Renewed.'
        else:
            # There's a slight chance this means the work wasn't
            # actually renewed, but more likely the dates are wrong in
            # the dataset.
            disposition = "Probably renewed, but registration dates don't match."
    else:
        # Too many renewals. Figure it out later.
        registration_output = not_yet_matched
        renewal_output = renewals_not_yet_matched
        disposition = None

    if disposition:
        data['disposition'] = disposition

    # A child registration can mean any number of things, and we don't
    # expect to have renewal information for all of a book's children.
    # That said, we should attach any information we do have.
    for child in children:
        child['renewals'] = []
        for child_regnum in child['regnums']:
            child['renewals'].extend(renewals_by_regnum[child_regnum])
        
    data['renewals'] = renewals
    json.dump(data, registration_output)
    registration_output.write("\n")
    if renewal_output:
        json.dump({num: renewals}, renewal_output)
        renewal_output.write("\n")
        

# Now that we're done, we can write a list of all the renewals that
# had no associated registration.
for regnum, renewals in renewals_by_regnum.items():
    if regnum not in seen_regnums:
        json.dump({regnum:renewals}, renewals_not_matched)
        renewals_not_matched.write("\n")
