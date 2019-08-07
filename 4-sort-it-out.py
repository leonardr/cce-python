from model import Registration
import json

class Output(object):
    def __init__(self, base):
        self.path = "output/FINAL-%s.ndjson" % base
        self.out = open(self.path, "w")
        self.count = 0

    def output(self, i):
        json.dump(i.jsonable(compact=True), self.out)
        self.out.write("\n")
        self.count += 1

    def tally(self, total, of_what):
        if not total:
            return "%s: %s" % (self.path, self.count)
        return "%s: %s (%.2f%% of %s)" % (
            self.path, self.count, self.count / float(total) * 100,
            of_what
        )

yes = Output("renewed")
probably = Output("probably-renewed")
possibly = Output("possibly-renewed")
no = Output("not-renewed")
foreign = Output("foreign")

def destination(file, disposition):
    if 'foreign' in file:
        return foreign
    if disposition.startswith("Probably renewed"):
        return probably
    if disposition.startswith("Probably not renewed"):
        return probably_not
    if disposition.startswith("Possibly renewed"):
        return possibly
    if disposition.startswith("Renewed"):
        return yes
    if disposition.startswith("Potentially foreign"):
        return potentially_foreign
    if disposition.startswith("Not renewed"):
        return no
    else:
        print disposition
        return no
    
for file in (
        "2-registrations-foreign",
        "3-potentially-foreign-registrations",
        "3-registrations-with-renewal",
        "3-registrations-with-no-renewal",
):
    path = "output/%s.ndjson"
    for i in open(path % file):
        data = Registration.from_json(json.loads(i))
        dest = destination(file, data.disposition)
        dest.output(data)

outputs = [yes, probably, possibly, no]
total = sum(x.count for x in outputs)
        
print(foreign.tally(total+foreign.count, "total"))
print("")
for output in outputs:
    print(output.tally(total, "US publications"))
