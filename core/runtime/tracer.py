"""
eBPF-based runtime tracer for AI/ML components.

This module uses eBPF to trace syscalls and capture real-time usage of
AI/ML artifacts like models, datasets, and prompts.
"""

import os
import json
import time
import threading
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

@dataclass
class RuntimeEvent:
    """Represents a runtime AI/ML artifact access event."""
    timestamp: float
    pid: int
    process_name: str
    syscall: str
    path: str
    source_url: Optional[str] = None
    artifact_type: Optional[str] = None  # model, dataset, prompt, tool
    hash: Optional[str] = None
    metadata: Optional[Dict] = None

class RuntimeTracer:
    """
    eBPF-based tracer for capturing AI/ML artifact usage at runtime.
    
    This tracer hooks into kernel syscalls to monitor file access and network
    calls that indicate AI/ML component usage.
    """
    
    # File extensions that indicate AI/ML artifacts
    ML_EXTENSIONS = {
        '.pt', '.pth', '.bin', '.safetensors', '.onnx', '.pb', '.h5',
        '.pkl', '.pickle', '.joblib', '.json', '.yaml', '.yml',
        '.csv', '.parquet', '.arrow', '.feather', '.txt', '.prompt'
    }
    
    # Path patterns that indicate AI/ML artifacts
    ML_PATHS = {
        '/models/', '/model/', '/checkpoints/', '/weights/',
        '/datasets/', '/data/', '/prompts/', '/templates/',
        '/.cache/huggingface/', '/.cache/torch/', '/.transformers_cache/'
    }
    
    # Network endpoints for AI/ML services
    ML_ENDPOINTS = {
        'huggingface.co', 'hf.co', 'cdn-lfs.huggingface.co',
        'openai.com', 'api.openai.com',
        'googleapis.com', 'generativelanguage.googleapis.com',
        'anthropic.com', 'api.anthropic.com'
    }
    
    def __init__(self, project_id: int, output_file: Optional[str] = None):
        self.project_id = project_id
        self.output_file = output_file or f"/tmp/mlbom_trace_{project_id}.json"
        self.events: List[RuntimeEvent] = []
        self.is_running = False
        self.tracer_thread: Optional[threading.Thread] = None
        self._bpf_available = self._check_bpf_availability()
        
    def _check_bpf_availability(self) -> bool:
        """Check if eBPF is available on the system."""
        try:
            # Check for BCC availability
            try:
                import bcc
                # Verify it's the right BCC (BPF Compiler Collection)
                if not hasattr(bcc, 'BPF'):
                    logger.warning("Installed bcc package is not the BPF Compiler Collection")
                    return False
                return True
            except ImportError:
                logger.warning("BCC not available, falling back to process monitoring")
                return False
        except Exception as e:
            logger.warning(f"Error checking BPF availability: {e}")
            return False
    
    def start(self) -> bool:
        """Start the runtime tracer."""
        if self.is_running:
            logger.warning("Tracer is already running")
            return False
            
        logger.info(f"Starting runtime tracer for project {self.project_id}")
        
        if self._bpf_available:
            return self._start_ebpf_tracer()
        else:
            return self._start_fallback_tracer()
    
    def _start_ebpf_tracer(self) -> bool:
        """Start eBPF-based tracer using BCC."""
        try:
            from bcc import BPF
            
            # eBPF program to trace file opens and network connections
            bpf_program = """
            #include <uapi/linux/ptrace.h>
            #include <linux/sched.h>
            #include <linux/fs.h>
            
            struct event_t {
                u32 pid;
                char comm[TASK_COMM_LEN];
                char filename[256];
                u64 ts;
            };
            
            BPF_PERF_OUTPUT(events);
            
            int trace_open(struct pt_regs *ctx, const char __user *filename, int flags) {
                struct event_t event = {};
                u32 pid = bpf_get_current_pid_tgid() >> 32;
                
                event.pid = pid;
                event.ts = bpf_ktime_get_ns();
                bpf_get_current_comm(&event.comm, sizeof(event.comm));
                bpf_probe_read_user_str(&event.filename, sizeof(event.filename), filename);
                
                events.perf_submit(ctx, &event, sizeof(event));
                return 0;
            }
            """
            
            self.bpf = BPF(text=bpf_program)
            self.bpf.attach_kprobe(event="do_sys_open", fn_name="trace_open")
            
            self.is_running = True
            self.tracer_thread = threading.Thread(target=self._process_ebpf_events)
            self.tracer_thread.daemon = True
            self.tracer_thread.start()
            
            logger.info("eBPF tracer started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start eBPF tracer: {e}")
            return self._start_fallback_tracer()
    
    def _start_fallback_tracer(self) -> bool:
        """Start fallback tracer using process monitoring."""
        logger.info("Starting fallback process monitor tracer")
        
        self.is_running = True
        self.tracer_thread = threading.Thread(target=self._process_monitor)
        self.tracer_thread.daemon = True
        self.tracer_thread.start()
        
        return True
    
    def _process_ebpf_events(self):
        """Process events from eBPF tracer."""
        def handle_event(cpu, data, size):
            try:
                import ctypes
                
                class EventData(ctypes.Structure):
                    _fields_ = [
                        ("pid", ctypes.c_uint32),
                        ("comm", ctypes.c_char * 16),
                        ("filename", ctypes.c_char * 256),
                        ("ts", ctypes.c_uint64)
                    ]
                
                event = ctypes.cast(data, ctypes.POINTER(EventData)).contents
                
                filename = event.filename.decode('utf-8', errors='ignore')
                process_name = event.comm.decode('utf-8', errors='ignore')
                
                if self._is_ml_artifact(filename):
                    runtime_event = RuntimeEvent(
                        timestamp=time.time(),
                        pid=event.pid,
                        process_name=process_name,
                        syscall="open",
                        path=filename,
                        artifact_type=self._classify_artifact(filename)
                    )
                    
                    self.events.append(runtime_event)
                    self._save_event(runtime_event)
                    
            except Exception as e:
                logger.error(f"Error processing eBPF event: {e}")
        
        if hasattr(self, 'bpf'):
            self.bpf["events"].open_perf_buffer(handle_event)
            
            while self.is_running:
                try:
                    self.bpf.perf_buffer_poll(timeout=100)
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    logger.error(f"Error in eBPF event loop: {e}")
                    break
    
    def _process_monitor(self):
        """Fallback process monitoring implementation."""
        import psutil
        
        monitored_processes: Set[int] = set()
        
        while self.is_running:
            try:
                # Monitor running processes for AI/ML activity
                for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'open_files']):
                    try:
                        pid = proc.info['pid']
                        name = proc.info['name'] or 'unknown'
                        
                        # Skip if already monitoring this process
                        if pid in monitored_processes:
                            continue
                            
                        # Check if process is likely doing ML work
                        if self._is_ml_process(proc.info):
                            monitored_processes.add(pid)
                            
                            # Check open files
                            try:
                                for file_info in proc.open_files():
                                    if self._is_ml_artifact(file_info.path):
                                        runtime_event = RuntimeEvent(
                                            timestamp=time.time(),
                                            pid=pid,
                                            process_name=name,
                                            syscall="open",
                                            path=file_info.path,
                                            artifact_type=self._classify_artifact(file_info.path)
                                        )
                                        
                                        self.events.append(runtime_event)
                                        self._save_event(runtime_event)
                                        
                            except (psutil.AccessDenied, psutil.NoSuchProcess):
                                pass
                                
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                # Clean up dead processes
                monitored_processes = {pid for pid in monitored_processes 
                                     if psutil.pid_exists(pid)}
                
                time.sleep(1)  # Poll every second
                
            except Exception as e:
                logger.error(f"Error in process monitor: {e}")
                time.sleep(5)
    
    def _is_ml_process(self, proc_info: Dict) -> bool:
        """Check if a process is likely doing ML work."""
        name = (proc_info.get('name') or '').lower()
        cmdline = ' '.join(proc_info.get('cmdline') or []).lower()
        
        ml_indicators = [
            'python', 'jupyter', 'torch', 'tensorflow', 'transformers',
            'huggingface', 'openai', 'anthropic', 'langchain', 'llama'
        ]
        
        return any(indicator in name or indicator in cmdline 
                  for indicator in ml_indicators)
    
    def _is_ml_artifact(self, path: str) -> bool:
        """Check if a file path represents an ML artifact."""
        path_lower = path.lower()
        
        # Check file extension
        path_obj = Path(path)
        if path_obj.suffix.lower() in self.ML_EXTENSIONS:
            return True
            
        # Check path patterns
        if any(pattern in path_lower for pattern in self.ML_PATHS):
            return True
            
        # Check for specific ML file patterns
        ml_patterns = [
            'model', 'checkpoint', 'weight', 'embedding',
            'dataset', 'prompt', 'template', 'config.json',
            'tokenizer', 'vocab', 'pytorch_model'
        ]
        
        return any(pattern in path_lower for pattern in ml_patterns)
    
    def _classify_artifact(self, path: str) -> str:
        """Classify the type of ML artifact based on path."""
        path_lower = path.lower()
        
        # Model files
        model_indicators = [
            '.pt', '.pth', '.bin', '.safetensors', '.onnx', '.pb', '.h5',
            'model', 'checkpoint', 'weight', 'pytorch_model'
        ]
        if any(indicator in path_lower for indicator in model_indicators):
            return 'model'
        
        # Dataset files
        dataset_indicators = [
            '.csv', '.parquet', '.arrow', '.feather', '.jsonl',
            'dataset', 'data', 'train', 'test', 'valid'
        ]
        if any(indicator in path_lower for indicator in dataset_indicators):
            return 'dataset'
        
        # Prompt files
        prompt_indicators = ['.prompt', '.txt', 'prompt', 'template', 'instruction']
        if any(indicator in path_lower for indicator in prompt_indicators):
            return 'prompt'
        
        # Configuration and tools
        tool_indicators = [
            'config.json', 'tokenizer', 'vocab', 'special_tokens',
            'generation_config', 'preprocessor_config'
        ]
        if any(indicator in path_lower for indicator in tool_indicators):
            return 'tool'
        
        return 'unknown'
    
    def _save_event(self, event: RuntimeEvent):
        """Save event to output file."""
        try:
            with open(self.output_file, 'a') as f:
                f.write(json.dumps(asdict(event)) + '\n')
        except Exception as e:
            logger.error(f"Failed to save event: {e}")
    
    def stop(self):
        """Stop the runtime tracer."""
        if not self.is_running:
            return
            
        logger.info("Stopping runtime tracer")
        self.is_running = False
        
        if self.tracer_thread:
            self.tracer_thread.join(timeout=5)
        
        if hasattr(self, 'bpf'):
            try:
                self.bpf.cleanup()
            except:
                pass
    
    def get_events(self) -> List[RuntimeEvent]:
        """Get all captured events."""
        return self.events.copy()
    
    def clear_events(self):
        """Clear all captured events."""
        self.events.clear()
        
        # Clear output file
        try:
            if os.path.exists(self.output_file):
                os.remove(self.output_file)
        except Exception as e:
            logger.error(f"Failed to clear output file: {e}")
    
    def get_summary(self) -> Dict:
        """Get a summary of captured events."""
        if not self.events:
            return {"total_events": 0}
        
        summary = {
            "total_events": len(self.events),
            "by_type": {},
            "by_process": {},
            "time_range": {
                "start": min(e.timestamp for e in self.events),
                "end": max(e.timestamp for e in self.events)
            }
        }
        
        for event in self.events:
            # Count by artifact type
            artifact_type = event.artifact_type or 'unknown'
            summary["by_type"][artifact_type] = summary["by_type"].get(artifact_type, 0) + 1
            
            # Count by process
            process = event.process_name
            summary["by_process"][process] = summary["by_process"].get(process, 0) + 1
        
        return summary