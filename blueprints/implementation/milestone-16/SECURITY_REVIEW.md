# Security Review

## Scans

Production Plugin SDK code scanned for:

- shell=True, os.system, eval, exec of untrusted input
- dynamic import from manifest without containment
- arbitrary module loading, sys.path mutation
- pip/pkg/apt install commands
- curl/wget/remote URLs
- public listener
- network access
- secret environment injection
- vault get
- policy bypass
- broker bypass
- capability wildcard
- auto-start, auto-enable
- arbitrary filesystem access
- cross-plugin access
- private signing key
- unbounded stdout
- unbounded retries

## Result

No production SDK code contains these unsafe patterns.
