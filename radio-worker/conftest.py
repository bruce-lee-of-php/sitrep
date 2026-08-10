import os
import sys
import types

# Ensure the radio-worker package root is importable as top-level modules
# (config, extract, sources, ...) when running pytest from anywhere.
sys.path.insert(0, os.path.dirname(__file__))

# Container-only dependencies (httpx, psycopg2, anthropic) may be absent in a
# bare local checkout. Stub any that are missing so the pure-logic unit tests
# (HTML parsing, extraction, id math) still run. When the real packages are
# installed (in the image) these stubs are never created.
for _dep in ("httpx", "psycopg2", "anthropic"):
    try:
        __import__(_dep)
    except ImportError:
        sys.modules[_dep] = types.ModuleType(_dep)
