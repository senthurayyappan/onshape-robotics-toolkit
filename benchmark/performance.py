import argparse
import logging
import subprocess
import time

logging.basicConfig(
    filename="benchmark.log",
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
)


def run_benchmark(script_path, iterations=1):
    """
    Run the specified script multiple times and measure its performance.

    :param script_path: Path to the script to benchmark.
    :param iterations: Number of times to run the script.
    """
    total_time = 0
    success_count = 0

    for i in range(1, iterations + 1):
        try:
            logging.info(f"Starting iteration {i} for {script_path}")
            start_time = time.time()
            # Redirect stdout and stderr to suppress output
            subprocess.run(["python", script_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)  # noqa: S603 S607
            elapsed_time = time.time() - start_time
            total_time += elapsed_time
            success_count += 1
            print(f"Iteration {i}: {script_path} completed in {elapsed_time:.2f} seconds")
            logging.info(f"Iteration {i} completed in {elapsed_time:.2f} seconds")
        except subprocess.CalledProcessError as e:
            print(f"Iteration {i}: An error occurred while running {script_path}: {e}")

    if success_count > 0:
        average_time = total_time / success_count
        print(f"\n{script_path} completed {success_count}/{iterations} runs successfully.")
        print(f"Average time: {average_time:.2f} seconds")
        logging.info(
            f"{script_path} completed {success_count}/{iterations} runs successfully. "
            f"Average time: {average_time:.2f} seconds"
        )
    else:
        print(f"\nAll runs of {script_path} failed.")
        logging.error(f"All runs of {script_path} failed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark a Python script.")
    parser.add_argument(
        "script_path",
        type=str,
        help="Path to the Python script to benchmark.",
    )
    parser.add_argument(
        "-n",
        "--iterations",
        type=int,
        default=1,
        help="Number of iterations to run the script (default: 1).",
    )
    args = parser.parse_args()

    run_benchmark(args.script_path, args.iterations)
