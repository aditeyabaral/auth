"""Script to test the unauthenticated CSRF token expiry."""

import argparse
import os
import time

from tqdm.auto import tqdm
from util import make_request, resolve_output_path


def test_response(response: dict, no_profile: bool) -> bool:
    """Test the response from the authenticate endpoint.

    Args:
        response (dict): The response from the authenticate endpoint.
        no_profile (bool): Whether to fetch the profile information or not.

    Returns:
        bool: True if the response is successful, False otherwise.
    """
    if response.get("status"):
        if not no_profile:
            return response.get("profile").get("prn") == os.getenv("TEST_PRN")
        return True
    return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test unauthenticated CSRF token expiry.")
    parser.add_argument(
        "--host",
        type=str,
        default="http://localhost:5000",
        help="The host to make the request to (default: http://localhost:5000)",
    )
    parser.add_argument(
        "--no-profile",
        action="store_true",
        help="Run the authenticate endpoint benchmark without fetching profile information "
        "(default: fetch profile info)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="The timeout for the request (default: 10)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="The base interval between requests (default: 10 minutes)",
    )
    parser.add_argument(
        "--start-delay",
        type=int,
        default=0,
        help="The delay before starting the benchmark (default: 0 minutes)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="The output file to save the results to (default: an auto-named CSV)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        help="The directory to write results into (default: benchmark/results at the repository root)",
    )
    parser.add_argument(
        "--tag",
        type=str,
        help="An identifier appended to the generated filename, for telling runs apart",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print the response for each request",
    )
    args = parser.parse_args()

    request_count, success, times, waiting_times = (
        0,
        list(),
        list(),
        [args.start_delay * 60],
    )

    for _ in tqdm(
        range(args.start_delay * 60),
        desc=f"Waiting {args.start_delay} minutes before starting the benchmark",
        leave=False,
        unit="s",
    ):
        time.sleep(1)

    outfile = resolve_output_path(
        script_name="unauthenticated_csrf_token_expiry",
        extension="csv",
        output=args.output,
        output_dir=args.output_dir,
        tag=args.tag,
    )

    # Each row is written as it is measured rather than after the loop ends. This script sleeps for
    # hours between requests, so buffering everything until the end means a Ctrl-C -- or anything
    # else that interrupts a long run -- throws away every measurement taken so far.
    with open(outfile, "w", buffering=1) as f:
        f.write("status,time,waiting_time\n")
        while True:
            request_count += 1
            response, elapsed = make_request(
                host=args.host,
                timeout=args.timeout,
                profile=not args.no_profile,
                route="authenticate",
            )
            status = int(test_response(response, args.no_profile))
            success.append(status)
            times.append(elapsed)
            f.write(f"{status},{elapsed},{waiting_times[-1]}\n")
            if args.verbose:
                print(f"Response: {response}")

            if status == 0:
                break

            next_interval = args.interval * request_count * 60
            for _ in tqdm(
                range(next_interval),
                desc=f"Waiting {next_interval / 60} minutes before next request",
                leave=False,
                unit="s",
            ):
                time.sleep(1)
            waiting_times.append(next_interval)

    print(f"Results saved to: {outfile}")
