# Identifying Public Domain Works with Python

This set of Python scripts combines [copyright registration
data](https://github.com/NYPL/catalog_of_copyright_entries_project)
with [copyright renewal data](https://github.com/NYPL/cce-renewals/)
to identify works whose copyright has lapsed.

The data comes from datasets provided by the New York Public
Library. These datasets build on work done by [the Internet
Archive](https://archive.org/details/copyrightrecords), [Stanford
Libraries](https://exhibits.stanford.edu/copyrightrenewals), and
[Project Gutenberg](https://www.gutenberg.org/ebooks/author/141).

# Statistics

* There are about 760,000 works where a renewal record would be
  necessary for the work to still be in copyright today.
* Of these, about 20% definitely have a renewal record and are still
  in copyright.
* About 7% _seem_ to have a renewal record, but a manual inspection is
  necessary to make sure.
* About 72% definitely have no renewal record.
* About 0.2% don't _seem_ to have a renewal record, but a manual
  inspection is necessary to make sure.

# Generating the Data

First, clone this repository and initialize the submodules. This will
bring in the raw registration and renewal data; it'll take a long
time.

```
git submodule init registrations
git submodule init renewals
```

Make sure the lxml XML parser is installed:

```
pip install -r requirements.txt
```

Then run the scripts, one after another:

```
python 0-parse-registrations.py
python 1-parse-renewals.py
python 2-normalize.py
python 3-handle-easy-cases.py
python 4-handle-multiple-renewals.py
python 5-sort-it-out.py
```

At the end of this process, you'll see a number of large files in the
`output` directory. These files represent the work product of each
step in the process. The files you're most likely interested in are
the `FINAL-` series, which represent this project's final conclusions
about which books were renewed and which weren't.

If you think there's been a mistake or a bad assumption somewhere in
this process, it's easy to fix. Change the corresponding script,
re-run it, then re-run the subsequent scripts to get a new set of
`FINAL-` files.

# How it works

I'll cover each script in order.

## `0-parse-registrations.py`

This script converts each copyright registration record from XML to
JSON, with a minimum of processing.

Outputs:

* `0-parsed-registrations.ndjson` - A list of registration records, each in
  JSON format.

## `1-parse-renewals.py`

This script converts each copyright renewal record from CSV to JSON,
with a minimum of processing.

Outputs:

* `1-parsed-renewals.ndjson` - A list of renewal records, each in JSON
  format.

## `2-normalize.py`

Normalize the registration data so that it's easier to compare with
the renewal data.

Remove registrations from consideration if there's clearly no point
in checking for a renewal.

Outputs:

* `2-registrations-after-1963.ndjson`: Copyright registrations that
  happened after 1963. These were renewed automatically, so there's no
  point in checking for an explicit renewal.

* `2-registrations-before-{year}.ndjson` - Registrations that are moot
  because they happened more than 95 years ago. These books are in the
  public domain regardless of whether the copyright was
  renewed, so there's no point checking for a renewal.

* `2-registrations-foreign.ndjson` - Registrations for foreign works,
  or for works where the place of publication was obviously a place
  outside the United States. These works are generally subject to
  different rules and there's no point checking for a renewal.

* `2-registrations-interim.ndjson` - Interim registrations, which are
  subject to different rules. There's no point checking for a renewal.

* `2-registrations-in-range.ndjson` - Registrations where the absence
  of a renewal record could make the difference between still being
  in-copyright and being in the public domain.

* `2-registrations-error.ndjson` - Contains data on a very small
  number of registrations which can't be processed because they're
  missing essential information.

## `3-handle-easy-cases.py`

This script takes `2-registrations-in-range.ndjson` as input, and
compares the registration information against the renewal information
from `1-parsed-renewals.ndjson`.

Most of the time, this check is really easy. Either there is a renewal
(the book is still in copyright) or there isn't (the copyright has
lapsed). This script handles all of these easy cases and leaves a much
smaller set of difficult cases for the next script to process.

Outputs:

* `3-registrations-with-no-renewal.ndjson` - Registrations with no
  corresponding renewal. These books are almost certainly in the public
  domain.

* `3-registrations-with-renewal.ndjson` - Registrations with an
  obvious corresponding renewal. These books are almost certainly
  still under copyright.
  
* `3-registrations-to-check.ndjson` - The difficult cases.
  These will be handled in the next script.

* `3-renewals-not-yet-matched.ndjson` - A list of renewals where we
  found no corresponding registration. These are mostly periodicals
  and such -- works other than "books proper" -- so their
  registrations aren't in the dataset.

## `4-handle-multiple-renewals.py`

This script handles the cases where multiple renewals were found for a
single registration ID. Generally speaking, this isn't supposed to
happen, but we can make a guess as to whether one of the renewals is
the one we're looking for, or whether they're all false positives and
the registration was not renewed at all.

Outputs:

* `4-probably-renewed.ndjson` - We're pretty sure we were able to find
  a renewal for this work, so it's probably in copyright -- but it
  needs to be checked manually.
* `4-probably-not-renewed.ndjson` - None of the renewals look like a
  match, so this work is probably out of copyright -- but it needs to
  be checked manually.

## `5-sort-it-out.py`

This simple script takes the output files generated by steps 3 and 4,
and consolidates them into four files:

* `FINAL-renewed.ndjson`: These books were almost certainly renewed
  and are still under copyright.
* `FINAL-not-renewed.ndjson`: These books were almost certainly not
  renewed and are now in the public domain.
* `FINAL-probably-renewed.ndjson`: These books were probably renewed,
  but a manual check is necessary to make sure.
* `FINAL-probably-not-renewed.ndjson`: These books were probably not
  renewed, but a manual check is necessary to make sure.

These files represent the final product. At this point you can take
one or more of them and use them in your own research.
