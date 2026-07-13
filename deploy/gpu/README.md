# GPU pool — AMD Developer Cloud MI300X runbook

Serves **Qwen2.5-72B-Instruct in full BF16 on ONE MI300X** (192 GB HBM3 — no
quantization, no tensor parallelism) behind an API key, as a `models.yaml` entry the
router discovers automatically.

## Verified session results (2026-06-30, 1× MI300X droplet @ $1.99/hr)

| Check | Result |
|---|---|
| vLLM (ROCm image) serving 72B BF16, hermes tool parser | ✅ up in ~5 min after downloads |
| Public endpoint auth | ✅ bearer key required; anonymous → 401 |
| `scripts/smoke_pool.py` (real agent loop: tools + guardrail) | ✅ PASS — tool call round-tripped, 12 grounded items, price verified |
| Live routing | ✅ router **chose** `amd-qwen-72b` for hard turns (cheapest heavy-class) |
| Cost/turn (amortized pricing) | ~$0.0004 — **98% below Sonnet** |
| Throughput (batch-1, untuned) | ~12 tok/s decode; multi-round project-planner turn 24.7 s end-to-end |
| **Failover** (container killed mid-service) | ✅ turn transparently retried on Sonnet (`escalated=true`), pool marked unhealthy, later turns route around it |

## Bring-up (~10 min + downloads on a fresh droplet)

1. Create GPU Droplet: **1× MI300X**, AMD AI/ML-ready image, SSH key auth. Note the IP.
2. `scp deploy/gpu/setup_droplet.sh root@<ip>:/root/`
3. `ssh root@<ip> "VLLM_API_KEY=<random-hex> bash /root/setup_droplet.sh"`
   (pulls `rocm/vllm`, pre-downloads weights with hf_transfer, starts the container,
   waits for `/v1/models`).
4. Point the app at it (any host — laptop or the HF Space via secrets):
   ```
   LOCAL_POOL_BASE_URL=http://<ip>:8000/v1
   LOCAL_POOL_API_KEY=<the same key>
   ```
5. Gate it before trusting it: `python -m scripts.smoke_pool amd-qwen-72b` must PASS.

## Teardown — read this

The droplet bills **hourly from create until DESTROY** (powered-off still bills;
~$2/hr ≈ $48/day idle). **Destroy the droplet after every session.** Weights re-download
on the next bring-up (~15 min at datacenter speeds).

## Notes / tuning headroom

- 12 tok/s is batch-1 BF16 with default flags; headroom: fp8 KV cache, larger batches
  (continuous batching shines under concurrency), `--max-model-len` tuning.
- First-token latency on tool turns is dominated by multi-round prefills (~8k tokens of
  tools+catalog context per round), not decode.
- The same runbook works for the QLoRA/LoRA artifacts (Stage 4): add
  `--enable-lora --lora-modules buildright-7b=<path>` and a second `models.yaml` entry.
