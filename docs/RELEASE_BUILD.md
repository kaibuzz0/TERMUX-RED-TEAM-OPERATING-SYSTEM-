# Release Build

Build a release with:

```bash
hive release build --source . --output ./dist --version 1.0.0 --sequence 1
```

The builder:

1. validates the version
2. builds a canonical manifest
3. creates a deterministic tar archive
4. writes unsigned metadata and manifest alongside

Sign separately with an offline key.
