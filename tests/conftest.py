import os
import socket
import subprocess
import time

import pytest

PORT = 8787

# main.pyの初期化（環境変数チェック）を通過するためのダミー値
os.environ["CLOUDFLARE_ACCOUNT_ID"] = "test-account-id"
os.environ["CLOUDFLARE_API_TOKEN"] = "test-api-token"
os.environ["CLOUDFLARE_DATABASE_ID"] = "test-database-id"
os.environ["CF_D1_BASE_URL"] = f"http://localhost:{PORT}"


def is_port_open(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


@pytest.fixture(scope="session", autouse=True)
def manage_wrangler_dev():
    # ポートがすでに開いている場合は新しく起動しない
    if is_port_open(PORT):
        yield
        return

    # ポートが開いていない場合は npx wrangler dev --port PORT を起動
    cmd = "npx.cmd" if os.name == "nt" else "npx"
    args = [cmd, "wrangler", "dev", "--port", str(PORT)]

    process = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=(os.name == "nt"),
    )

    # 起動を待つ (最大10秒)
    retries = 20
    started = False
    for _ in range(retries):
        if is_port_open(PORT):
            started = True
            break
        time.sleep(0.5)

    if not started:
        # 起動失敗時はプロセスを終了してエラー
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(process.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            process.terminate()
            process.wait()
        raise RuntimeError(f"Failed to start wrangler dev on port {PORT}")

    yield

    # テスト終了時にプロセスをクリーンアップ
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
