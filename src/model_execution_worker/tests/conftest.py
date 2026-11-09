import pytest


@pytest.fixture(autouse=True)
def _in_process_oasislmf_calls(monkeypatch):
    """Run `isolated.run_isolated` calls in-process so tests can mock oasislmf.

    Tests of the isolation itself re-enable it with OASIS_WORKER_ISOLATED_EXECUTION=True.
    """
    monkeypatch.setenv('OASIS_WORKER_ISOLATED_EXECUTION', 'False')
