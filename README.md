# Identifying Public Domain Works with Python

This set of Python scripts combines [copyright registration
data](https://github.com/NYPL/catalog_of_copyright_entries_project)
with [copyright renewal data](https://github.com/NYPL/cce-renewals/)
to identify works whose copyright has lapsed because a registration
was not renewed.

The data comes from datasets provided by the New York Public
Library. These datasets build on work done by [the Internet
Archive](https://archive.org/details/copyrightrecords), [Stanford
Libraries](https://exhibits.stanford.edu/copyrightrenewals), and
[Project Gutenberg](https://www.gutenberg.org/ebooks/author/141).

Thanks are due to [Sean Redmond](https://github.com/seanredmond),
[Josh Hadro](https://github.com/hadro), and Greg Cram.

# Statistics

* There are about 840,000 works where a renewal record would be
  necessary for the work to still be in copyright today.
* Of these, about 19% definitely have a renewal record and are still
  in copyright.
* About 8% _seem_ to have a renewal record, but a manual inspection is
  necessary to make sure.
* About 73% definitely have no renewal record.

# Generating the Data

First, clone this repository and initialize the submodules. This will
bring in the raw registration and renewal data; it'll take a long
time.

```
git submodule init
git submodule update
```

Make sure the lxml XML parser is installed:

```
pip install -r requirements.txt
```

Then run the scripts, one after another:

```
python 0-parse-registrations.py
python 1-parse-renewals.py
python 2-filter.py
python 3-locate-renewals.py
python 4-sort-it-out.py
```

The final script's output will look something like this:

```
output/FINAL-foreign.ndjson: 193364 (18.78% of total)

output/FINAL-renewed.ndjson: 158539 (18.96% of US publications)
output/FINAL-probably-renewed.ndjson: 1112 (0.13% of US publications)
output/FINAL-possibly-renewed.ndjson: 62430 (7.47% of US publications)
output/FINAL-not-renewed.ndjson: 614095 (73.44% of US publications)
```

You'll see a number of large files in the `output` directory. These
files represent the work product of each step in the process. The
files you're most likely interested in are the `FINAL-` series,
mentioned above. These files represent this project's final
conclusions about which books were renewed and which weren't; which
books were published in the US and which weren't.

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

## `2-filter.py`

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
  interim registrations (used while foreign works were looking for a
  US publisher), and registrations where the place of publication
  looks like a place outside the United States. Foreign works had
  their copyright renewed by treaty, so the absence of a renewal
  doesn't prove anything.

* `2-registrations-in-range.ndjson` - Registrations where the absence
  of a renewal record could make the difference between still being
  in-copyright and being in the public domain.

* `2-cross-references-in-foreign-registrations` - References in a
  registration for a foreign publication to _other_ registrations. Those other
  registrations might also be foreign publications -- we'll check
  that in the next step.

* `2-registrations-error.ndjson` - Contains about 20,000 registrations
  which can't be processed because they're missing essential
  information. This information might be missing from the original
  registrations, it might be missing from the transcription, or the
  information might be represented in a form that these scripts can't
  understand.

## `3-locate-renewals.py`

This script takes `2-registrations-in-range.ndjson` as input, and
compares the registration information against the renewal information
from `1-parsed-renewals.ndjson`.

Most of the time, this check is really easy. Either there is a renewal
(the book is still in copyright) or there isn't (the copyright has
lapsed). But sometimes the renewal looks like it might actually be for
a different book. Sometimes there are _multiple_ renewals, and all of
them look bad. This script does the best it can.

Outputs:

* `3-registrations-with-no-renewal.ndjson` - Registrations for
  US-published works with no corresponding renewal at all. These books
  are almost certainly in the public domain.

* `3-registrations-with-renewal.ndjson` - Registrations for
  US-published works where at least one corresponding renewal was
  found. This includes books where we're really certain about the
  match between registration and renewal, books where we're fairly
  certain, and books where it doesn't look like the renewals
  have anything to do with the original publication.

* `3-potentially-foreign-registrations.ndjson` - These registrations
  were mentioned in a registration for a foreign publication, so we're
  assuming they're also foreign publications. They'll need to be checked
  manually.

* `3-renewals-with-no-registrations.ndjson` - A list of renewals we
  didn't match to a registration. Some of these are pamphlets and such
  -- works other than "books proper" -- so although their
  registrations exist, they aren't in this dataset. Some of them are
  renewals for foreign publications, which we eliminated from
  consideration before even looking at renewals. Others may represent
  missing data or errors.

## `4-sort-it-out.py`

This simple script takes the output files generated by steps 2 and 3,
and consolidates them into four files:

* `FINAL-foreign.ndjson`: These books appear to be foreign
   publications, or were mentioned in a foreign publication, so we
   didn't even check to see if they had renewal records.
* `FINAL-not-renewed.ndjson`: These books were almost certainly not
  renewed and are now in the public domain.
* `FINAL-probably-renewed.ndjson`: These books were probably renewed,
  but a manual check is necessary to make sure.
* `FINAL-possibly-renewed.ndjson`: These books had one or more renewal
  records, but none of them seemed like a good match. A manual check
  is necessary to verify that these 

These files represent the final work product. At this point you can take
one or more of them and use them in your own research.

# Dispositions

Each JSON object in the `FINAL-` files has a `disposition` key that
explains this script's final conclusion about its renewal status. Here
are the possible dispositions:

* `Not renewed.` - No renewal record was found, and we saw no
   complicating factors. The copyright on this book has
   almost certainly lapsed.

* `Renewed (date match).` - A renewal was found which has a date match
  with the original registration. That's almost certainly the 'real'
  renewal, and if so, this book is still in copyright.

* `Probably renewed (author match).` - There was no date match, but
  one of the renewals has the same author as the one mentioned in this
  registration. That's probably the 'real' renewal, and if so, this
  book is still in copyright.

* `Probably renewed (title match).` - There was no date or author
  match, but one of the renewals has a similar title to the one
  mentioned in the registration. That's probably the 'real' renewal,
  and if so, this book is still in copyright.

* `Possibly renewed, but none of these renewals seem like a good
   match.` - One or more renewals was found based on the registration
   ID, but the other data doesn't match. Since renewal IDs were reused
   over time, this may or may not mean that this particular
   publication had its copyright renewed. It needs to be checked
   manually.

* `Foreign publication.` - There's strong evidence that this work is a
  foreign publication. If so, then its copyright was restored by
  treaty and the presence or absence of a renewal is irrelevant.

* `Possible foreign publication - check manually.` - This work was
  mentioned in the registration record for a foreign publication. This
  may mean that it, itself, is a foreign publication. It needs to be
  checked manually.

* `Classified with parent.` - This work was grouped beneath another
  registration, and the parent registration was removed from
  consideration -- probably because it was post-1963 or because it was
  a foreign work. In the absence of strong evidence to the contrary,
  all of its children were also removed from consideration, but they
  were given a different `disposition` in case you want to check them
  manually.
