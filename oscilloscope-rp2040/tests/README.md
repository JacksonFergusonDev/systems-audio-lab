# Contents

- **`test_imports.py`**: A quick check that the `sysaudio` package imports. If it fails, the usual causes are a circular import or a missing `__init__.py`.
- **`test_deconvolution.py`**: ESS inverse filter regression tests: a perfect loopback must deconvolve flat, a known low-pass must be recovered, and pure delay must shift the impulse peak exactly.
- **`test_chunked_sweep.py`**: Simulates stream-mode captures (gapped, jittered 1024-sample blocks) and checks that chunked sweep analysis recovers the block period, reports no harmonics for a clean sweep, and recovers a known low-pass response and the analytic harmonics of a polynomial nonlinearity.
- **`test_transfer_curve.py`**: Checks that transfer-curve preparation removes the ADC bias and aligns delayed captures.

## Running Tests

The tests run with `pytest`.

### Using `uv` (Recommended)

```bash
# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v
```
