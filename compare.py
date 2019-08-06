from collections import defaultdict
from model import Registration, Renewal

class Comparator(object):
    def __init__(
        self, renewals_input_path, foreign_registrations_input_path:
    ):
        self.registrations = []
        self.renewals_by_regnum = defaultdict(list)
        for i in open(renewals_input_path):
            renewal = Renewal(**json.loads(i))
            renewals_by_regnum[renewal.regnum].append(renewal)

        self.foreign_registrations_by_regnum = defaultdict(list)
        for i in open(reference_in_foreign_registrations_path):
            registration = Registration(**json.loads(i))
            for regnum in registration.regnum:
                self.foreign_registrations_by_regnum[regnum].append(registration)

    def check(self, registration):
        set_trace()
        pass

