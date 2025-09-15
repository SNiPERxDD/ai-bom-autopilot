# Runtime AI-BOM Tracing

This module implements eBPF-based syscall tracing to capture AI/ML components actually used at runtime.

## Components

- `tracer.py`: eBPF syscall tracer for file access and network calls
- `normalizer.py`: Normalizes runtime events to AI artifacts
- `collector.py`: Collects and processes runtime events

## Features

- **Real-time Tracing**: Captures model loads, dataset access, prompt usage
- **Low Overhead**: eBPF provides kernel-level tracing with minimal performance impact
- **Filtering**: Smart filtering to reduce noise and focus on AI/ML artifacts
- **Integration**: Seamlessly integrates with existing static analysis workflow

## Usage

```python
from core.runtime.tracer import RuntimeTracer

tracer = RuntimeTracer(project_id=1)
tracer.start()  # Begin tracing
# ... run your ML application ...
events = tracer.get_events()
tracer.stop()
```