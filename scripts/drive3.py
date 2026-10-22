"""Interleaved Alpine vs slim-bookworm vs slim-trixie benchmark: latency breakdown, CPU and memory per request."""

import json
import subprocess
import sys
import time
from pathlib import Path

import httpx2

REPO = Path("/home/aditeyabaral/Desktop/pesu/auth")
sys.path.insert(0, str(REPO / "scripts" / "benchmark"))
from util import make_request  # noqa: E402

OUT = REPO / "benchmark" / "results" / "alpine_slim_trixie"
OUT.mkdir(parents=True, exist_ok=True)

IMAGES = {
    "alpine": ("pesu-auth:bench-alpine", 5001),
    "slim": ("pesu-auth:bench-slim", 5002),
    "trixie": ("pesu-auth:bench-trixie", 5003),
}
# ABC CBA BCA ACB: every image sums to position 22, and each triad holds one block of each
ORDER = [{"A": "alpine", "B": "slim", "C": "trixie"}[c] for c in "ABCCBABCAACB"]
BLOCK = 25
COLD_TRIALS = 6  # each image starts first, second and third twice


def sh(*args: str) -> str:
    done = subprocess.run(args, capture_output=True, text=True)
    if done.returncode:
        raise RuntimeError(f"{args[:3]} failed: {done.stderr.strip()}")
    return done.stdout.strip()


def cgroup(cid: str) -> Path:
    return Path(f"/sys/fs/cgroup/system.slice/docker-{cid}.scope")


def cpu_usec(cid: str) -> dict[str, int]:
    stat = dict(line.split() for line in (cgroup(cid) / "cpu.stat").read_text().splitlines())
    return {k: int(stat[k]) for k in ("usage_usec", "user_usec", "system_usec")}


def mem(cid: str, pid: int) -> dict[str, int]:
    cg = cgroup(cid)
    mstat = dict(line.split() for line in (cg / "memory.stat").read_text().splitlines())
    status = dict(
        (line.split(":")[0], int(line.split()[1]))
        for line in Path(f"/proc/{pid}/status").read_text().splitlines()
        if line.startswith(("VmRSS", "VmHWM"))
    )
    return {
        "cg_current": int((cg / "memory.current").read_text()),
        "cg_peak": int((cg / "memory.peak").read_text()),
        "cg_anon": int(mstat["anon"]),
        "rss_kb": status["VmRSS"],
        "hwm_kb": status["VmHWM"],
    }


def start(name: str, port: int) -> tuple[str, int, float]:
    image = IMAGES[name][0]
    t0 = time.perf_counter()
    cid = sh("docker", "run", "-d", "--rm", "--name", f"pesu-bench-{name}-{port}-{time.time_ns()}", "-p", f"{port}:5000", image)
    while True:
        try:
            if httpx2.get(f"http://localhost:{port}/health", timeout=1).status_code == 200:
                break
        except httpx2.HTTPError:
            pass
        time.sleep(0.01)
    ready = time.perf_counter() - t0
    pid = int(sh("docker", "inspect", "-f", "{{.State.Pid}}", cid))
    return cid, pid, ready


def metrics(port: int) -> dict:
    return httpx2.get(f"http://localhost:{port}/metrics?fmt=json", timeout=5).json()


def sums(m: dict) -> dict[str, float]:
    route = m["requestsByRoute"].get("POST /authenticate", {"latency": {"sumSeconds": 0.0}})
    # Upstream families appear only after the first call to PESU
    up = m.get("upstream", {})
    return {
        "server": route["latency"]["sumSeconds"],
        "login": up.get("login", {}).get("latency", {}).get("sumSeconds", 0.0),
        "profile": up.get("profile_fetch", {}).get("latency", {}).get("sumSeconds", 0.0),
    }


def main() -> None:
    # Static sizes
    static = {}
    for name, (image, _) in IMAGES.items():
        info = json.loads(sh("docker", "image", "inspect", image))[0]
        listing = json.loads(sh("docker", "image", "ls", "--format", "{{json .}}", image).splitlines()[0])
        gz = subprocess.run(f"docker save {image} | gzip -6 | wc -c", shell=True, check=True,
                            capture_output=True, text=True).stdout
        openssl = sh("docker", "run", "--rm", "--entrypoint", "python", image, "-c",
                     "import ssl, platform; print(ssl.OPENSSL_VERSION, platform.libc_ver())")
        static[name] = {
            "gzip_bytes": int(gz),
            "openssl": openssl,
            "image_size_bytes": info["Size"],
            "layers": len(info["RootFS"]["Layers"]),
            "image_ls": listing,
        }

    # Cold starts, alternating, no PESU traffic
    cold = []
    for trial in range(COLD_TRIALS):
        names = list(IMAGES)
        for name in names[trial % 3 :] + names[: trial % 3]:
            cid, pid, ready = start(name, 5010)
            time.sleep(3)
            cold.append({"image": name, "trial": trial, "ready_s": ready, **mem(cid, pid)})
            sh("docker", "rm", "-f", cid)
    (OUT / "cold_start.json").write_text(json.dumps(cold, indent=2))
    print("cold starts done", flush=True)

    # Long-running containers for the interleaved run
    procs = {}
    for name, (_, port) in IMAGES.items():
        cid, pid, ready = start(name, port)
        procs[name] = (cid, pid, port)
    time.sleep(5)
    idle = {name: mem(cid, pid) for name, (cid, pid, _) in procs.items()}
    idle_cpu = {name: cpu_usec(cid) for name, (cid, _, _) in procs.items()}

    rows = []
    run_started = time.perf_counter()
    blocks = [("warmup", n, 1) for n in IMAGES] + [(i, n, BLOCK) for i, n in enumerate(ORDER)]
    block_meta = []
    for block, name, count in blocks:
        cid, pid, port = procs[name]
        b_cpu0, b_t0 = cpu_usec(cid), time.perf_counter()
        before = sums(metrics(port))
        for i in range(count):
            started = time.perf_counter() - run_started
            c0 = cpu_usec(cid)
            try:
                body, elapsed = make_request(host=f"http://localhost:{port}", profile=True, timeout=10.0)
                ok = 1 if body.get("status") and body.get("profile") else 0
            except Exception as e:  # noqa: BLE001
                print(f"{name} request failed: {type(e).__name__}", flush=True)
                ok, elapsed = 0, float("nan")
            c1 = cpu_usec(cid)
            m = mem(cid, pid)
            after = sums(metrics(port))
            rows.append({
                "image": name, "block": block, "i": i, "start": started, "status": ok,
                "client_s": elapsed,
                "server_s": after["server"] - before["server"],
                "login_s": after["login"] - before["login"],
                "profile_s": after["profile"] - before["profile"],
                "cpu_ms": (c1["usage_usec"] - c0["usage_usec"]) / 1000,
                "cpu_user_ms": (c1["user_usec"] - c0["user_usec"]) / 1000,
                "cpu_sys_ms": (c1["system_usec"] - c0["system_usec"]) / 1000,
                **m,
            })
            before = after
        b_cpu1, b_t1 = cpu_usec(cid), time.perf_counter()
        block_meta.append({
            "block": block, "image": name, "wall_s": b_t1 - b_t0,
            "cpu_s": (b_cpu1["usage_usec"] - b_cpu0["usage_usec"]) / 1e6,
        })
        print(f"block {block} {name} done", flush=True)

    final = {}
    for name, (cid, pid, _) in procs.items():
        size = json.loads(sh("docker", "inspect", "--size", cid))[0]
        stats = json.loads(sh("docker", "stats", "--no-stream", "--format", "{{json .}}", cid))
        final[name] = {
            "mem": mem(cid, pid), "cpu": cpu_usec(cid), "idle_cpu": idle_cpu[name], "idle_mem": idle[name],
            "size_rw": size.get("SizeRw"), "size_rootfs": size.get("SizeRootFs"), "docker_stats": stats,
            "metrics": metrics(procs[name][2]),
        }
        sh("docker", "rm", "-f", cid)

    import pandas as pd

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "requests.csv", index=False)
    (OUT / "meta.json").write_text(json.dumps({"static": static, "final": final, "blocks": block_meta}, indent=2))
    # Same columns benchmark_requests.py writes, so analyze_benchmark.py can read them
    for name in IMAGES:
        part = df[(df.image == name) & (df.block != "warmup")]
        part.rename(columns={"client_s": "time"})[["status", "time", "start"]].to_csv(
            OUT / f"{name}.csv", index=False
        )
    print("done", flush=True)


if __name__ == "__main__":
    main()
