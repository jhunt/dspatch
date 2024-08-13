create table if not exists tasks (
  job_id        text not null,
  batch_id      text not null,
  task_number   integer not null,
  details       variant,
  requested_at  timestamp default current_timestamp,
  started_at    timestamp default null,
  finished_at   timestamp default null,
  status_code   text      default 'requested'
);

drop view if exists current_tasks;
create view current_tasks as
with
latest as (select job_id, max(requested_at) as requested_at
             from tasks group by job_id)
select tasks.*
  from tasks
  join latest
    on tasks.job_id = latest.job_id
   and tasks.requested_at = latest.requested_at
 order by job_id asc, task_number asc
;

drop view if exists current_status;
create view current_status as
select job_id,
       batch_id,
       sum(case when started_at  is     null then 1 else 0 end) as ntasks_not_started,
       sum(case when started_at  is not null
                 and finished_at is     null then 1 else 0 end) as ntasks_started,
       sum(case when finished_at is not null then 1 else 0 end) as ntasks_finished,
       count(*) as ntasks_total
  from current_tasks
 group by job_id, batch_id
 order by job_id asc
;

create table if not exists api_keys (
  shared_key      text,
  enabled_after   timestamp,
  disabled_after  timestamp,
  notes           text
);
drop view if exists in_force_api_keys;
create view in_force_api_keys as
select shared_key as key
  from api_keys
 where current_timestamp between enabled_after
                             and disabled_after
;
