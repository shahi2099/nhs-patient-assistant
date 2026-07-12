.PHONY: update-data download chunk ingest

update-data: download chunk ingest

download:
	uv run python src/nhs_download.py

chunk:
	uv run python src/nhs_chunking_data.py

ingest:
	uv run python src/ingest.py
