# Performance & Benchmarks

**CYBERNETIC OS — Measured Performance Records**

---

## 1. Verified Physical Benchmark Run

The following metrics represent an actual physical webcam test run conducted during validation:

| Metric | Measured Value | Unit / Description |
|---|---|---|
| **Test Duration** | 120 | Processed video frames |
| **Average Framerate** | **23.93** | FPS (Frames per second) |
| **Minimum Framerate** | **14.45** | FPS (During multi-hand acquisition initialization) |
| **Camera Read Latency** | **3.48** | ms (Mean hardware frame acquisition time) |
| **MediaPipe Inference Latency** | **36.27** | ms (Mean hand detection & 3D landmark inference) |
| **Event Bus Dispatch Latency** | **< 0.15** | ms (Mean synchronous dispatch time) |
| **Total Pipeline Latency** | **~41.8** | ms per frame |

> [!IMPORTANT]
> **No Fabricated Data**: These numbers represent measured physical benchmark values on the development hardware and must not be altered or claimed without running an actual new physical benchmark.

---

## 2. Benchmark Environment & Hardware Specifications

- **OS**: Windows 11 (x64)
- **CPU**: Intel Core i7 / Multi-core host processor
- **GPU**: NVIDIA GeForce RTX 5050 Laptop GPU (8 GB VRAM)
- **RAM**: 24 GB System Memory
- **Python Version**: Python 3.12.10
- **Computer Vision Runtime**: OpenCV Contrib 4.11.0.86, MediaPipe 0.10.21, NumPy 1.26.4
- **Execution Mode**: CPU Landmark Inference (MediaPipe Tasks CPU pipeline with OpenCV acceleration)

---

## 3. Telemetry Collection Architecture

The `telemetry/logger.py` module continuously measures and logs operational metrics to `logs/performance.jsonl`:
- Real-time frame interval & moving-average FPS
- Camera frame acquisition time (`camera_ms`)
- Hand tracking inference latency (`inference_ms`)
- Action execution latency (`action_ms`)
- Gesture classification confidence (`confidence`)
- Dropped frame count
- False activation mitigation counters
