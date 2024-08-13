dspatch
=======

This app is meant to run on loopback and be accessible to other
parts of a larger architecture, for background processes.  It
operates on a global namespace of Jobs, each with multiple
Batches.  Each Batch consists of one or more Tasks.

For any given Job, only one Batch is "current" at any given point
in time; if a new Batch is created, it supersedes all of the other
Batches and any unstarted Tasks will be scuttled.

New Jobs are created when their first Batch is built, using
something like this:

```console
$ curl https://ds.example.com/work/job1/batch1 \
       -H 'Authorization: API-Key 12345' \
       -H 'Content-Type: application/json' \
       -H 'Accept: application/json' \
       --data-binary '[{"op":98},{"op":99}]'
```

Examples in this readme will assume that the dspatch instance is
accessible at https://ds.example.com, and that the API key of
`12345` has been properly provisioned for access.  For more
details on API keys, see below.

The POST body is a list of task details.  The specifics are of
interest only to consumers and workers; dspatch doesn't care what
type of object, what keys, etc., so long as a top-level list is
supplied.

To see the status of the current Batch for a Job named `job1`:

```console
$ curl https://ds.example.com/status/job1 \
       -H 'Authorization: API-Key 12345' \
       -H 'Accept: application/json'

{
  "batch_id": "batch1",
  "is_done": true,
  "is_running": false,
  "job_id": "job1",
  "ntasks_finished": 2,
  "ntasks_not_started": 0,
  "ntasks_started": 0,
  "ntasks_total": 2
}
```

Some external actor needs to play the part of the worker process,
requesting chunks of tasks from the current batch and operating on
them.  To get the next 10 things to work on:

```console
$ curl https://ds.example.com/next/job1/10 \
       -H 'Authorization: API-Key 12345' \
       -H 'Accept: application/json'

[
  {
    "batch_id": "batch1",
    "details": {
      "op": 98
    },
    "job_id": "job1",
    "task_number": 1
  },
  {
    "batch_id": "batch1",
    "details": {
      "op": 99
    },
    "job_id": "job1",
    "task_number": 2
  }
]
```

To start one or more jobs, post their task numbers in a list to
the `/start/` endpoint:

```console
$ curl https://ds.example.com/start/job1/batch1/started \
       -H 'Authorization: API-Key 12345' \
       -H 'Accept: application/json' \
       -H 'Content-Type: application/json' \
       --data-binary '[1,2]'
```

This causes the returned jobs to be put into a _started_ state.
If those tasks cannot be completed, they should be abandoned:

```console
$ curl https://ds.example.com/abandon/job1/batch1 \
       -H 'Authorization: API-Key 12345' \
       -H 'Accept: application/json' \
       -H 'Content-Type: application/json' \
       --data-binary '[2]'
```

As work items are completed, mark them as such via:

```console
$ curl https://ds.example.com/finish/job1/batch1/done \
       -H 'Authorization: API-Key 12345' \
       -H 'Accept: application/json' \
       -H 'Content-Type: application/json' \
       --data-binary '[1]'
```

Note that both `/start/` and `/finish/` require a _status_
parameter, as the last component of the URI, but `/abandon/`
does not; if you are abandoning a task, the only status that makes
sense is "abandoned".

## API Keys

API Keys are managed in the SQL database.  There is no user
interface (neither web nor CLI) for dealing with them.  I
personally use the `sqlite3` command-line and just write the SQL
to interrogate and manipulate the keystore.

Those queries are:

```sql
-- create a new valid api key of '12345'
insert into api_keys (shared_key, enabled_after, disabled_after)
  values ('12345', current_timestamp, '2030-12-31 23:59:59');

-- disable the api key 'c0mpr0m1s3d'
update api_keys
   set disabled_after = current_timestamp
 where shared_key = 'c0mpr0m1s3d';
```

Clients wishing to use an API key must supply an Authorization
header with a value formatted like this:

`API-Key $KEY`

where `$KEY` is the API key in the database's `shared_key` column.
No extra spacing is allowed.  The checker is VERY strict.

For example, to use the first key in the example above via curl,
you would run:

```console
$ curl -H 'Authorization: API-Key 12345' \
       # ... etc ...
```

The second key would not work, given that its `disabled_after`
date is now in the past.

## Operationalizing

A sample Docker Compose recipe is included in `contrib/`; use it
if you find it helpful, but please vet security and performance
characteristics before you do anything serious with it.
