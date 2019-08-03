import json

class Output(object):
    def __init__(self, base):
        self.path = "output/FINAL-%s.ndjson" % base
        self.out = open(self.path, "w")
        self.count = 0

    def output(self, i):
        self.out.write(i)
        self.count += 1

    def tally(self, total):
        return "%s: %s (%.2f%%)" % (
            self.path, self.count, self.count / float(total) * 100
        )
        
probably = Output("probably-renewed")
probably_not = Output("probably-not-renewed")
yes = Output("renewed")
no = Output("not-renewed")

def destination(disposition):
    if disposition.startswith("Probably renewed"):
        return probably
    if disposition.startswith("Probably not renewed"):
        return probably_not
    if disposition.startswith("Renewed"):
        return yes
    if disposition.startswith("Not renewed"):
        return no

for file in (
        "3-registrations-with-renewal",
        "3-registrations-with-no-renewal",
        "4-probably-renewed",
        "4-probably-not-renewed",
):
    path = "output/%s.ndjson"
    for i in open(path % file):
        data = json.loads(i)
        dest = destination(data['disposition'])
        dest.output(i)

outputs = [yes, no, probably, probably_not]
total = sum(x.count for x in outputs)
        
for output in outputs:
    print(output.tally(total))
