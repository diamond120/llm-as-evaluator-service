import argparse
import workers.worker_concurrent as concurrent_run
import workers.worker_linear as linear_run


def main():
    parser = argparse.ArgumentParser(
        description="Pass the process handler type either --worker-type= 'concurrent' or 'linear'."
    )
    parser.add_argument(
        "--worker_type",
        type=str,
        default="concurrent",
        help="The type of worker to be used.",
    )

    args = parser.parse_args()

    if args.worker_type == "linear":
        print("Starting linear worker")
        linear_run.main()

    elif args.worker_type == "concurrent":
        print("Starting concurrent worker")
        concurrent_run.main()


if __name__ == "__main__":
    main()
