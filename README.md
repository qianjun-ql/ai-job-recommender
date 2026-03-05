## Setup

git clone ...
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env # fill in your keys
make ingest
make test



Data source:
https://www.kaggle.com/code/enricofindley/linkedin-job-postings-2023-data-analysis/input
https://www.kaggle.com/datasets/joykimaiyo18/linkedin-data-jobs-dataset/data
https://www.kaggle.com/datasets/kanchana1990/ai-and-ml-job-listings-usa
