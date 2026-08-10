import subprocess
import sys

print("=== python ===", sys.version)

try:
    import torch
except ImportError:
    print("TORCH_IMPORT: FAILED")
    raise

print("=== torch ===", torch.__version__)
print("CUDA_AVAILABLE:", torch.cuda.is_available())
print("DEVICE_COUNT:", torch.cuda.device_count())

if torch.cuda.is_available():
    for i in range(torch.cuda.device_count()):
        print(f"DEVICE[{i}]:", torch.cuda.get_device_name(i))
    # Real proof, not just the flag: actually allocate and compute on the GPU.
    x = torch.randn(2048, 2048, device="cuda")
    y = torch.randn(2048, 2048, device="cuda")
    z = (x @ y).sum().item()
    print("GPU_MATMUL_OK:", z)
else:
    print("GPU_MATMUL_OK: SKIPPED (no CUDA device)")

print("=== nvidia-smi ===")
try:
    out = subprocess.run(["nvidia-smi"], capture_output=True, text=True, timeout=20)
    print(out.stdout or out.stderr)
except Exception as exc:
    print("nvidia-smi failed:", exc)

print("SMOKE_TEST_DONE")
