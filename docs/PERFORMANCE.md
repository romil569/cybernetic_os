# Performance & Benchmarks

**CYBERNETIC OS — Measured Performance Records**

---

## 1. Verified Physical Benchmark Run

| Metric | Measured Value | Unit / Description |
|---|---|---|
| **Test Duration** | 120 | Processed video frames |
| **Average Framerate** | **23.93** | FPS (Frames per second) |
| **Minimum Framerate** | **14.45** | FPS (During initialization) |
| **Camera Read Latency** | **3.48** | ms (Mean hardware frame acquisition time) |
| **MediaPipe Inference Latency** | **36.27** | ms (Mean landmark inference time) |
| **Event Bus Dispatch Latency** | **< 0.15** | ms (Mean synchronous dispatch time) |
| **Total Pipeline Latency** | **~41.8** | ms per frame |

---

## 2. Environment Specifications

- **OS**: Microsoft Windows 11
- **GPU**: NVIDIA GeForce RTX 5050 Laptop GPU (8 GB VRAM)
- **RAM**: 24 GB
- **Python**: 3.12.10
- **Libraries**: OpenCV Contrib 4.11.0.86, MediaPipe 0.10.21, NumPy 1.26.4
- **Log Location**: `logs/performance.jsonl`
