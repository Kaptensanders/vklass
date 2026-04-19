"""Shared pytest helpers for Vklass tests.

The previous placeholder imports pulled in the integration package during test
collection even when no helper was used. Keep this module import-safe so test
discovery does not fail on unrelated dependency issues.
"""
