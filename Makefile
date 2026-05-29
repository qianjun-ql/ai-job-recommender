.PHONY: ingest extract train train-jobbert embed api django frontend test eval

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

django:
	python frontend/django_backend/manage.py runserver 8001

frontend:
	cd frontend/react_app && npm run dev

test:
	pytest tests/ -v

eval:
	python eval/precision_at_k.py
