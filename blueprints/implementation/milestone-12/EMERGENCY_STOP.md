# Emergency Stop

`hive broker stop` writes a stop request atomically and marks transactions cancelled.

Stop semantics are cooperative and bounded:
- prevent further dispatcher steps
- record an audit event
- preserve evidence and subsystem state
- not terminate unrelated processes
- not kill services directly unless a future capability explicitly authorizes it

A stop token alone cannot cancel a blocking external operation; all operations must have timeouts.
