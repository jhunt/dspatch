#!/bin/sh
if [ "x${1}" = "x" ]; then
  test -f $DISPATCH_DATABASE \
  || cp /build/dispatch.db $DISPATCH_DATABASE
  ls -lh $DISPATCH_DATABASE

  exec flask run --host $BIND_HOST --port $BIND_PORT
  exit 7
fi

if [ -x $1 ]; then
  exec "$@"
  exit 8
fi

exec /bin/sh -c "$@"
exit 9
