import os, json, sqlite3
from flask import g, Flask, request, make_response, jsonify
from functools import wraps

DATABASE = os.getenv('DISPATCH_DATABASE', 'app.db')

def get_db():
  db = getattr(g, '_database', None)
  if db is None:
    db = g._database = sqlite3.connect(DATABASE)
  return db

def api_key_required(f):
  @wraps(f)
  def inner(*args, **kwargs):
    key = None
    if 'authorization' in request.headers and request.headers['authorization'].startswith('API-Key '):
      key = request.headers['authorization'][8:]
    if key is None:
      return make_response(jsonify({'error': 'Authorization header required'}), 401)
    r = get_db().cursor().execute('select key from in_force_api_keys where key = ?', (key,))
    if r.fetchone() is None:
      return make_response(jsonify({'error': 'Authorization key invalid'}), 403)
    return f(*args, **kwargs)
  return inner

app = Flask(__name__)

@app.teardown_appcontext
def close_connection(exception):
  db = getattr(g, '_database', None)
  if db is not None:
    db.close()

@app.route('/work/<job>/<batch>', methods=['POST'])
@api_key_required
def create_work(job, batch):
  data = []
  for detail in request.get_json():
    data.append((job, batch, 1+len(data), json.dumps(detail)))
  db = get_db()
  cur = db.cursor()
  cur.executemany('''
    insert into tasks (job_id, batch_id, task_number, details)
               values (?, ?, ?, ?)''', data)
  db.commit()
  return {'ok': 'created'}

@app.route('/next/<job>/<n>', methods=['GET'])
@api_key_required
def next_work(job, n):
  cur = get_db().cursor()
  # FIXME sanitize n
  r = cur.execute(f'''
    select job_id, batch_id, task_number, details
      from current_tasks
     where job_id = ?
       and started_at is null
     limit {n}''', (job,))
  response = []
  for (job_id, batch_id, task_number, details) in r:
    response.append({
      'job_id': job_id,
      'batch_id': batch_id,
      'task_number': task_number,
      'details': json.loads(details)
    })
  return response

@app.route('/start/<job>/<batch>/<status>', methods=['POST'])
@api_key_required
def start_work(job, batch, status):
  data = []
  for id in request.get_json():
    data.append((status, job, batch, id))

  db = get_db()
  cur = db.cursor()
  r = cur.executemany('''
    update tasks
       set status_code = ?,
           started_at  = current_timestamp,
           finished_at = null
           --
     where job_id      = ?
       and batch_id    = ?
       and task_number = ?''', data)
  db.commit()
  return {'ok': 'started'}

@app.route('/abandon/<job>/<batch>', methods=['POST'])
@api_key_required
def abandon_work(job, batch):
  data = []
  for id in request.get_json():
    data.append((job, batch, id))

  db = get_db()
  cur = db.cursor()
  r = cur.executemany('''
    update tasks
       set status_code = 'abandoned',
           started_at  = null,
           finished_at = null
           --
     where job_id      = ?
       and batch_id    = ?
       and task_number = ?''', data)
  db.commit()
  return {'ok': 'abandoned'}

@app.route('/finish/<job>/<batch>/<status>', methods=['POST'])
@api_key_required
def finish_work(job, batch, status):
  data = []
  for id in request.get_json():
    data.append((status, job, batch, id))

  db = get_db()
  cur = db.cursor()
  r = cur.executemany('''
    update tasks
       set status_code = ?,
           started_at  = coalesce(started_at, current_timestamp),
           finished_at = current_timestamp
           --
     where job_id      = ?
       and batch_id    = ?
       and task_number = ?''', data)
  db.commit()
  return {'ok': 'finished'}

@app.route('/status/<job>', methods=['GET'])
@api_key_required
def job_status(job):
  cur = get_db().cursor()
  r = cur.execute('''
    select batch_id,
           ntasks_not_started,
           ntasks_started,
           ntasks_finished,
           ntasks_total
      from current_status
     where job_id = ?''', (job,))
  (batch_id, ntasks_not_started, ntasks_started, ntasks_finished, ntasks_total) = (r.fetchone())
  return {
    'job_id': job,
    'batch_id': batch_id,
    'ntasks_not_started': ntasks_not_started,
    'ntasks_started': ntasks_started,
    'ntasks_finished': ntasks_finished,
    'ntasks_total': ntasks_total,
    'is_running': ntasks_started > 0,
    'is_done': ntasks_total == ntasks_finished
  }

