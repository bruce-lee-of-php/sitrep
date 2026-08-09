import os
import sys

# Ensure the radio-worker package root is importable as top-level modules
# (config, extract, sources, ...) when running pytest from anywhere.
sys.path.insert(0, os.path.dirname(__file__))
