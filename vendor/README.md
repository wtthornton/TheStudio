# vendor/

Vendored dependencies that aren't available on PyPI.

## ralph-sdk

Before building the Docker image, copy the ralph-sdk source into this directory:

```bash
# From the repo root:
cp -r /path/to/ralph-claude-code/sdk/* vendor/ralph-sdk/
```

The Dockerfile rewrites pyproject.toml at build time to point at `vendor/ralph-sdk`
instead of the local dev path.
