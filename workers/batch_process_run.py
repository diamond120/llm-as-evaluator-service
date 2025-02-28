import time
import json
import redis
import os
from common.utils import load_env
from workers.slim_tasks import process_run

env_vars = load_env()
redis_host = env_vars.get("REDIS_HOST", "localhost")
redis_port = int(env_vars.get("REDIS_PORT", 6379))
redis_db = int(env_vars.get("REDIS_DB", 0))
redis_client = redis.StrictRedis(host=redis_host, port=redis_port, db=redis_db)
SLOW_QUEUE_BATCH_COUNT = int(os.getenv("SLOW_QUEUE_BATCH_COUNT", 40))


def fetch_from_redis_queue(queue_name, count):
    """
    Fetch a batch of items from the Redis queue.
    """
    pipeline = redis_client.pipeline()
    for _ in range(count):
        pipeline.lpop(queue_name)
    items = pipeline.execute()
    return [item for item in items if item is not None]

def process_run_batch(batch):
    """
    Send batch of runs to process_run.
    """
    for item in batch:
        data = json.loads(item)  # Deserialize the item
        process_run.apply_async(
            args=[
                data["run_item"],
                data["evaluations"],
                data.get("aggregated_evaluations"),
            ],
            kwargs={"save_to_db": True},
            queue="bulk_process_queue"  # Replace with your actual queue name
        )

def consumer():
    """
    Consumer logic to process items from Redis queue.
    """
    queue_name = "bulk_batch_request"

    while True:
        try:
            # Fetch batch count from queues
            batch = fetch_from_redis_queue(queue_name, count=SLOW_QUEUE_BATCH_COUNT)
            if batch:
                # Process the batch
                process_run_batch(batch)
                print(f"Processed batch of {len(batch)} items.")
                print(f"Number of messages in bulk_evaluation_queue {redis_client.llen('bulk_evaluation_queue')}")
                print(f"Number of messages in bulk_saving_queue {redis_client.llen('bulk_saving_queue')}")
            else:
                print("Queue is empty, waiting...")

            # Sleep for 60 seconds
            time.sleep(60)
        except Exception as e:
            print(f"Error in consumer: {str(e)}")
            time.sleep(5)  # Sleep longer on error to avoid busy-waiting

if __name__ == "__main__":
    consumer()
