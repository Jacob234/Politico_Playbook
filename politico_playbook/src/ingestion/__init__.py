"""Multi-newsletter ingestion layer.

Replaces the single-source IMAP-based extraction (politico_playbook/src/extraction/)
with a Gmail API + SQLite + sender-slug-keyed registry design.

Entry point: politico_playbook.src.ingestion.runner.main
"""
