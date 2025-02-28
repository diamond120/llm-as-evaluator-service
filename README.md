# LLM as Evaluator Backend and Frontend Repo

## How to RUn the API service?

1. Clone the repo, Create a venv, and `pip install -r requirements.txt`
2. Activate the venv created in step1,
3. Run `uvicorn app.main:app --reload` in the project directory (Api service runs)
4. Open another terminal and run the workers (Step 5)
5. From project directory, run the below commands

   `export PYTHONPATH=$PYTHONPATH:$(pwd)`  
    `python workers/worker.py`
   (This will consume messages from pub/sub and run the evaluation)
6. To run custom worker to process bulk message in slow queue, run the following commands

   `export PYTHONPATH=$PYTHONPATH:$(pwd)`
    `python workers/batch_process_run.py`

Notes:
Use Bearer token to run the api service
========================
