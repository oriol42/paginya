"""Shared by every test: the pictures of a presentation are found at once, not in a background thread, so a test
sees them when the call returns (one test turns the background back on to check it)."""
import os

os.environ.setdefault("PAGINYA_PICTURES_LATER", "0")
