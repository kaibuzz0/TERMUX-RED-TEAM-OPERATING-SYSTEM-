# Dashboard Safety Review

**Milestone 5 — `Hive Ops Final/bin/hive-dashboard`**

## Classification

SAFE FOR PATH-ONLY REPAIR — with the caveat that it is not required for core startup, and its subprocess and `nc` usage should be reviewed before being promoted to a default command.

## Listener evidence

Patterns checked: ['socket.bind', '.bind(', '.listen(', 'serve_forever', 'HTTPServer', 'TCPServer', 'FastAPI', 'Flask', 'uvicorn', 'http.server', 'aiohttp', 'websockets.serve']
Found: None

**Conclusion:** NO LISTENER EVIDENCE

The dashboard uses `nc -z` to **probe** local SOCKS endpoints (127.0.0.1:9050/9051/9052). It does not bind or open a port itself.

## Subprocess usage

Patterns checked: ['subprocess', 'os.system', 'exec', 'eval']
Found: ['subprocess', 'os.system']

## Secret handling

Patterns checked: ['password', 'token', 'secret', 'key', 'credential']
Found: ['key']

## Hardcoded /root/ or root assumptions

Patterns checked: ['/root/', 'sudo', 'su -']
Found: ['/root/']

## `nc` probe lines


## Recommendations

- `hive-dashboard` remains **deferred** in Milestone 5.
- Its path assumptions can be repaired in a future milestone once the exact runtime contract is documented and tested.
- No dashboard modification is performed now.
- No listener is started.
