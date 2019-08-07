from pdb import set_trace
from collections import defaultdict
from model import Registration, Renewal
import json

class Comparator(object):
    def __init__(
        self, renewals_input_path, foreign_registrations_input_path
    ):
        self.foreign_registrations = defaultdict(list)
        for i in open(foreign_registrations_input_path):
            registration = Registration(**json.loads(i))
            for regnum in registration.regnums:
                self.foreign_registrations[regnum].append(registration)

        self.renewals = defaultdict(list)
        for i in open(renewals_input_path):
            renewal = Renewal(**json.loads(i))
            self.renewals[renewal.regnum].append(renewal)

        self.used_renewals = set()
       
    def is_foreign(self, registration):
        for regnum in registration.regnums:
            if regnum in self.foreign_registrations:
                registration.warnings.append(
                    "This registration was mentioned in a registration for a likely foreign publication. It's possible that this registration is also a foreign publication."
                )
                registration.extra['foreign_registration'] = self.foreign_registrations[regnum][0].jsonable()
                registration.disposition = "Possible foreign publication - check manually."
                return True
        return False

    def renewal_for(self, registration):
        """Find a renewal for this registration.
        
        If there's more than one, find the best one that meets minimum
        
        """
        renewals = []
        renewal = None
        for regnum in registration.regnums:
            if regnum in self.renewals:
                renewals.extend(self.renewals[regnum])
        if renewals:
            renewals, disposition = self.best_renewal(registration, renewals)
            registration.disposition = disposition
        else:
            registration.disposition = "Not renewed."
            renewals = []
        for renewal in renewals:
            # These renewals have been matched; they should not be
            # output in the list of unmatched renewals.
            self.used_renewals.add(renewal.regnum)
        return renewals

    def best_renewal(self, registration, renewals):
        # Find a renewal based on a registration date match.
        possibilities = [x.isoformat()[:10] for x in registration.registration_dates]
        for renewal in renewals:
            if renewal.reg_date in possibilities:
                # A very strong match.
                return [renewal], "Renewed. (Date match.)"

        # At this point we have multiple renewals and no date matches.
        # Try an author match.
        for renewal in renewals:
            if registration.author_match(renewal.author):
                return [renewal], "Probably renewed. (Author match.)"
        for renewal in renewals:
            if registration.title_match(renewal.title):
                return [renewal], "Probably renewed. (Title match.)"

        return renewals, "Possibly renewed, but none of these renewals seem like a good match."
