import asyncio
import time

import pytest
import runtime


async def test_worker():
    r = await runtime.execute(
        "resolver", {"problema": {"operacion": "derivada", "expresion": "x**2"}}
    )
    assert r["exacto"] == "2*x"


async def test_hard_timeout_and_recovery(monkeypatch, tmp_path):
    worker = tmp_path / "slow.py"
    worker.write_text("import time\ntime.sleep(30)\n")
    with monkeypatch.context() as patch:
        patch.setattr(runtime, "WORKER", worker)
        started = time.monotonic()
        out = await runtime.execute("resolver", {}, timeout=0.2)
        assert out["codigo"] == "tiempo" and time.monotonic() - started < 3
    assert (
        await runtime.execute(
            "resolver", {"problema": {"operacion": "derivada", "expresion": "x"}}
        )
    )["exacto"] == "1"


async def test_busy_and_cancel(monkeypatch, tmp_path):
    worker = tmp_path / "slow.py"
    worker.write_text("import time\ntime.sleep(30)\n")
    with monkeypatch.context() as patch:
        patch.setattr(runtime, "WORKER", worker)
        task = asyncio.create_task(runtime.execute("resolver", {}, timeout=5))
        await asyncio.sleep(0.1)
        assert (await runtime.execute("resolver", {}))["codigo"] == "ocupado"
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert not runtime._gate.locked()


async def test_input_size():
    assert (await runtime.execute("resolver", {"x": "x" * 24001}))[
        "codigo"
    ] == "entrada"
