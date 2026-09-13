# pesu-auth

[![Docker Image Build](https://github.com/pesu-dev/auth/actions/workflows/docker.yaml/badge.svg)](https://github.com/pesu-dev/auth/actions/workflows/docker.yml)
[![Pre-Commit Checks](https://github.com/pesu-dev/auth/actions/workflows/pre-commit.yaml/badge.svg)](https://github.com/pesu-dev/auth/actions/workflows/pre-commit.yaml)
[![Lint](https://github.com/pesu-dev/auth/actions/workflows/lint.yaml/badge.svg)](https://github.com/pesu-dev/auth/actions/workflows/lint.yaml)
[![Deploy](https://github.com/pesu-dev/auth/actions/workflows/deploy-prod.yaml/badge.svg)](https://github.com/pesu-dev/auth/actions/workflows/deploy-prod.yaml)

[![Docker Automated build](https://img.shields.io/docker/automated/pesudev/pesu-auth?logo=docker)](https://hub.docker.com/r/pesudev/pesu-auth/builds)
[![Docker Image Version (tag)](https://img.shields.io/docker/v/pesudev/pesu-auth/latest?logo=docker&label=build%20commit)](https://hub.docker.com/r/pesudev/pesu-auth/tags)
[![Docker Image Size (tag)](https://img.shields.io/docker/image-size/pesudev/pesu-auth/latest?logo=docker)](https://hub.docker.com/r/pesudev/pesu-auth)

A simple and lightweight API to authenticate PESU credentials using PESU Academy.

The API is secure and protects user privacy by not storing any user credentials. It only validates credentials and
returns the user's profile information. No personal data is stored.

## PESUAuth LIVE Deployment

- You can access the PESUAuth API endpoints [here](https://pesu-auth.onrender.com/).
- You can view the health status of the API on the [PESUAuth Health Dashboard](https://xzlk85cp.status.cron-job.org/).

#### API Status

![Cron job status](https://api.cron-job.org/jobs/4424640/69701a6f8df1d307/status-7.svg)\
![Cron job status](https://api.cron-job.org/jobs/6338038/9feb0f217be714ec/status-7.svg)\
![Cron job status](https://api.cron-job.org/jobs/5672615/1d744f1dc18fb505/status-7.svg)\
![Cron job status](https://api.cron-job.org/jobs/4424663/d5a30351867acec9/status-7.svg)

> [!NOTE]
> All timestamps are in UTC.

> [!WARNING]
> The live version is hosted on a free tier server located in the United States. As a result, you *might* experience higher latencies and slower response times, compared to running the API locally or on a server closer to your location.

## How to run PESUAuth locally

Running the PESUAuth API locally is simple. Clone the repository and follow the steps below to get started.

> [!TIP]
> We recommend running the API locally using Docker for ease of use, the best performance, and lowest latency.

### Running with Docker

This is the easiest and recommended way to run the API locally. Ensure you have Docker installed on your system. Run the
following commands to start the API.

1. Build the Docker image either from the source code or pull the pre-built image from Docker Hub.

   1. You can build the Docker image from the source code by running the following command in the root directory of
      the repository.

      ```bash
      docker build . --tag pesu-auth
      ```

   1. You can also pull the pre-built Docker image
      from [Docker Hub](https://hub.docker.com/repository/docker/pesudev/pesu-auth/general) by running the
      following command:

      ```bash
      docker pull pesudev/pesu-auth:latest
      ```

1. Run the Docker container

   ```bash
   docker run --name pesu-auth -d -p 5000:5000 pesu-auth
   # If you pulled the pre-built image, use the following command instead:
   docker run --name pesu-auth -d -p 5000:5000 pesudev/pesu-auth:latest
   ```

1. Access the API at `http://localhost:5000/`

### Running without Docker

If you don't have Docker installed, you can run the API natively. Ensure you have Python 3.14 or higher
installed on your system. We recommend using a package manager like [`uv`](https://docs.astral.sh/uv/) to manage
dependencies.

1. Create a virtual environment using and activate it. Then, install the dependencies using the following commands.

   ```bash
   uv venv --python=3.14
   source .venv/bin/activate
   uv sync
   ```

1. Run the API using the following command.

   ```bash
   uv run python -m app.app
   ```

1. Access the API as previously mentioned on `http://localhost:5000/`

## How to use the PESUAuth API

The API provides multiple endpoints for authentication, documentation, and monitoring.

| **Endpoint**    | **Method** | **Description**                                        |
| --------------- | ---------- | ------------------------------------------------------ |
| `/`             | `GET`      | Serves the interactive API documentation (Swagger UI). |
| `/authenticate` | `POST`     | Authenticates a user using their PESU credentials.     |
| `/health`       | `GET`      | A health check endpoint to monitor the API's status.   |
| `/metrics`      | `GET`      | Exposes traffic and error counters. See `fmt` below.   |
| `/readme`       | `GET`      | Redirects to the project's official GitHub repository. |

### `/authenticate`

You can send a request to the `/authenticate` endpoint with the user's credentials and the API will return a JSON
object, with the user's profile information if requested.

#### Request Parameters

| **Parameter** | **Optional** | **Type**    | **Default** | **Description**                                                                                 |
| ------------- | ------------ | ----------- | ----------- | ----------------------------------------------------------------------------------------------- |
| `username`    | No           | `str`       |             | The user's SRN or PRN                                                                           |
| `password`    | No           | `str`       |             | The user's password                                                                             |
| `profile`     | Yes          | `boolean`   | `False`     | Whether to fetch profile information                                                            |
| `fields`      | Yes          | `list[str]` | `None`      | Which fields to fetch from the profile information. If not provided, all fields will be fetched |

#### Response Object

On authentication, it returns the following parameters in a JSON object. If the authentication was successful and
profile data was requested, the response's `profile` key will store a dictionary with a user's profile information.
**On an unsuccessful sign-in, this field will not exist**.

| **Field**   | **Type**        | **Description**                                                          |
| ----------- | --------------- | ------------------------------------------------------------------------ |
| `status`    | `boolean`       | A flag indicating whether the overall request was successful             |
| `profile`   | `ProfileObject` | A nested map storing the profile information, returned only if requested |
| `message`   | `str`           | A message that provides information corresponding to the status          |
| `timestamp` | `datetime`      | A timezone offset timestamp indicating the time of authentication        |

##### `ProfileObject`

This object contains the user's profile information, which is returned only if the `profile` parameter is set to `True`.
If the authentication fails, this field will not be present in the response.

| **Field**    | **Description**                                        |
| ------------ | ------------------------------------------------------ |
| `name`       | Name of the user                                       |
| `prn`        | PRN of the user                                        |
| `srn`        | SRN of the user                                        |
| `program`    | Academic program that the user is enrolled into        |
| `branch`     | Complete name of the branch that the user is pursuing  |
| `semester`   | Current semester that the user is in                   |
| `section`    | Section of the user                                    |
| `email`      | Email address of the user registered with PESU         |
| `phone`      | Phone number of the user registered with PESU          |
| `campusCode` | The integer code of the campus (1 for RR and 2 for EC) |
| `campus`     | Abbreviation of the user's campus name                 |

### `/health`

This endpoint can be used to check the health of the API. It's useful for monitoring and uptime checks. This endpoint
does not take any request parameters.

#### Response Object

| **Field**   | **Type**   | **Description**                                                     |
| ----------- | ---------- | ------------------------------------------------------------------- |
| `status`    | `boolean`  | `true` if healthy, `false` if there was an error                    |
| `message`   | `str`      | "ok" if healthy, error message otherwise                            |
| `timestamp` | `datetime` | A timezone offset timestamp indicating the time of the health check |

### `/metrics`

This endpoint exposes counters describing the traffic this process has served, in the
[Prometheus text exposition format](https://prometheus.io/docs/instrumenting/exposition_formats/) by default, ready
to be scraped, or as JSON with `?fmt=json`.

```
# HELP pesu_auth_responses_total HTTP responses, by status code.
# TYPE pesu_auth_responses_total counter
pesu_auth_responses_total{status="200"} 1094
pesu_auth_responses_total{status="401"} 160
```

The counters live in memory and **reset when the process restarts**, which is why
`pesu_auth_process_start_time_seconds` is exposed: without it a dashboard cannot tell a restart from a drop in traffic.
Status codes and exception classes are recorded separately, so errors that share a status code — `CSRFTokenError` and
`ProfileFetchError` are both `502` — stay distinguishable.

Requests to `/metrics` are themselves counted. Excluding them would mean the endpoint reported a request total that did
not match the sum of its own response counts.

#### Query Parameters

| **Field** | **Type** | **Description**                                                                        |
| --------- | -------- | -------------------------------------------------------------------------------------- |
| `fmt`     | `str`    | `prometheus` (default) for the text exposition format, or `json` for the same counters |

#### Response Object (`fmt=json`)

| **Field**           | **Type** | **Description**                                                            |
| ------------------- | -------- | -------------------------------------------------------------------------- |
| `startTimeSeconds`  | `float`  | Start time of this process since the Unix epoch. Counters reset on restart |
| `uptimeSeconds`     | `float`  | Seconds since this process started collecting                              |
| `requests`          | `object` | `total`, `success` and `failed` request counts                             |
| `latency`           | `object` | `sumSeconds`, `count` and `averageSeconds` until a response starts         |
| `authentication`    | `object` | `total`, `withProfile` and `withoutProfile` authentication request counts  |
| `responsesByStatus` | `object` | Response counts keyed by HTTP status code                                  |
| `requestsByRoute`   | `object` | Per-route requests and latency, keyed by `"METHOD route-template"`         |
| `errorsByType`      | `object` | Error counts keyed by exception class name                                 |

`requests.total` counts a request on arrival while the outcome is recorded on completion, so `total` can briefly exceed
`success + failed` while requests are in flight.

### `/readme`

This endpoint redirects to the project's official GitHub repository. This endpoint does not take any request parameters.

### Integrating your application with the PESUAuth API

Here are some examples of how you can integrate your application with the PESUAuth API using Python and cURL.

#### Python

##### Request

```python
import requests

data = {
    "username": "your SRN or PRN here",
    "password": "your password here",
    "profile": True,  # Optional, defaults to False
}

response = requests.post("http://localhost:5000/authenticate", json=data)
print(response.json())
```

##### Response

```json
{
  "status": true,
  "profile": {
    "name": "Johnny Blaze",
    "prn": "PES1201800001",
    "srn": "PES1201800001",
    "program": "Bachelor of Technology",
    "branch": "Computer Science and Engineering",
    "semester": "NA",
    "section": "NA",
    "email": "johnnyblaze@gmail.com",
    "phone": "1234567890",
    "campusCode": 1,
    "campus": "RR"
  },
  "message": "Login successful.",
  "timestamp": "2024-07-28 22:30:10.103368+05:30"
}
```

#### cURL

##### Request

```bash
curl -X POST http://localhost:5000/authenticate \
-H "Content-Type: application/json" \
-d '{
    "username": "your SRN or PRN here",
    "password": "your password here"
}'
```

#### Response

```json
{
  "status": true,
  "message": "Login successful.",
  "timestamp": "2024-07-28 22:30:10.103368+05:30"
}
```

## Contributing to PESUAuth

Made with ❤️ by

[![Contributors](https://contrib.rocks/image?repo=pesu-dev/auth&nocache=1)](https://github.com/pesu-dev/auth/graphs/contributors)

*Powered by [contrib.rocks](https://contrib.rocks)*

If you'd like to contribute, please follow our [contribution guidelines](.github/CONTRIBUTING.md).
