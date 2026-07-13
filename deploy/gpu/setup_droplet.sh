#!/usr/bin/env bash
# One-shot setup for the AMD Developer Cloud MI300X GPU droplet (AMD AI/ML-ready image).
# Serves Qwen2.5-72B-Instruct in BF16 on ONE MI300X (192GB — no quantization, no TP)
# behind an API key, with tool calling enabled for the BuildRight agent loop.
#
#   scp deploy/gpu/setup_droplet.sh root@<ip>:/root/ && ssh root@<ip> "VLLM_API_KEY=xxx bash /root/setup_droplet.sh"
#
# Billing discipline: the droplet bills ~$1.99/hr from create to DESTROY (power-off
# still bills). Destroy after each session; this script makes re-creation ~10 min +
# downloads.
set -euo pipefail

: "${VLLM_API_KEY:?Set VLLM_API_KEY}"
MODEL="${MODEL:-Qwen/Qwen2.5-72B-Instruct}"
MAX_LEN="${MAX_LEN:-16384}"

mkdir -p /root/hf-cache /root/logs

echo "== pulling ROCm vLLM image (skips if present) =="
docker pull rocm/vllm:latest

echo "== pre-downloading model weights (skips existing files) =="
pip3 install -q --break-system-packages 'huggingface_hub[hf_transfer]'
HF_HOME=/root/hf-cache HF_HUB_ENABLE_HF_TRANSFER=1 python3 - <<PY
from huggingface_hub import snapshot_download
snapshot_download("${MODEL}", max_workers=16)
PY

echo "== starting vLLM =="
docker rm -f vllm 2>/dev/null || true
docker run -d --name vllm --restart unless-stopped \
  --device=/dev/kfd --device=/dev/dri --group-add video \
  --cap-add=SYS_PTRACE --security-opt seccomp=unconfined \
  --ipc=host --shm-size 32g \
  -p 8000:8000 \
  -v /root/hf-cache:/root/.cache/huggingface \
  -e HF_HOME=/root/.cache/huggingface \
  rocm/vllm:latest \
  vllm serve "${MODEL}" \
    --api-key "${VLLM_API_KEY}" \
    --enable-auto-tool-choice --tool-call-parser hermes \
    --max-model-len "${MAX_LEN}" \
    --gpu-memory-utilization 0.92

echo "== waiting for the server (weight load ≈ 3-6 min) =="
until curl -sf -H "Authorization: Bearer ${VLLM_API_KEY}" http://localhost:8000/v1/models > /dev/null 2>&1; do
  sleep 10
done
echo "vLLM is UP: $(curl -s -H "Authorization: Bearer ${VLLM_API_KEY}" http://localhost:8000/v1/models | head -c 200)"
