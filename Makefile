.PHONY: ingest extract train train-jobbert embed api ui test eval

ingest:
	python pipelines/ingest.py

extract:
	python pipelines/extract_skills.py

train-jobbert:
	python pipelines/train_jobbert.py --epochs 15 --batch-size 4

train: train-jobbert

embed:
	python pipelines/embed.py

api:
	uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

ui:
	streamlit run ui/app.py

test:
	pytest tests/ -v

eval:
	python eval/precision_at_k.py
