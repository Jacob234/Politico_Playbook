"""Multi-newsletter ingestion layer.

Gmail API + SQLite + sender-slug-keyed registry. Replaced the single-source
IMAP-based v0.1 extraction layer; v0.1 preserved at git tag
v0.1-poc-single-source.

Entry point: politico_playbook.ingestion.runner.main
"""
