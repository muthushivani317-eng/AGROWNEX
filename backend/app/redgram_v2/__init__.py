"""Superseded, unvalidated Redgram V2 candidate with an unopened sealed test.

This is not the deployed Redgram disease runtime. The active restricted runtime is
``redgram_mobilenetv3_small_v1_restricted``.
"""

from .runtime import RedgramRuntime, get_redgram_runtime

__all__ = ["RedgramRuntime", "get_redgram_runtime"]
