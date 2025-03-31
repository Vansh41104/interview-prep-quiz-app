from datetime import datetime
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict
import json

@dataclass
class APICall:
    timestamp: datetime
    service: str
    endpoint: str
    status: str
    duration: float
    cost: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    model: str = "unknown"
    prompt_size: int = 0  # Size of prompt in characters

class APITracker:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(APITracker, cls).__new__(cls)
            cls._instance.initialize()
        return cls._instance
    
    def initialize(self):
        self.calls: List[APICall] = []
        self.service_costs = defaultdict(float)
        self.total_cost = 0.0
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
    def track_call(self, service: str, endpoint: str, status: str, duration: float, cost: float = 0.0, 
                  input_tokens: int = 0, output_tokens: int = 0, model: str = "unknown", prompt_size: int = 0):
        """Track an API call with its details"""
        total_tokens = input_tokens + output_tokens
        call = APICall(
            timestamp=datetime.now(),
            service=service,
            endpoint=endpoint,
            status=status,
            duration=duration,
            cost=cost,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            model=model,
            prompt_size=prompt_size
        )
        self.calls.append(call)
        self.service_costs[service] += cost
        self.total_cost += cost
        self.total_tokens += total_tokens
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        
        # Print to terminal
        print(f"\n[API Call] {service} - {endpoint}")
        print(f"Status: {status}")
        print(f"Duration: {duration:.2f}s")
        print(f"Model: {model}")
        print(f"Tokens: {input_tokens} input, {output_tokens} output, {total_tokens} total")
        print(f"Prompt size: {prompt_size} characters")
        if cost > 0:
            print(f"Cost: ${cost:.4f}")
        print(f"Total {service} cost: ${self.service_costs[service]:.4f}")
        print(f"Total API cost: ${self.total_cost:.4f}")
        print(f"Total tokens used: {self.total_tokens} (Input: {self.total_input_tokens}, Output: {self.total_output_tokens})")
        print("-" * 50)
    
    def get_summary(self) -> Dict:
        """Get a summary of all API calls"""
        return {
            "total_calls": len(self.calls),
            "total_cost": self.total_cost,
            "total_tokens": self.total_tokens,
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "service_costs": dict(self.service_costs),
            "calls_by_service": self._get_calls_by_service(),
            "calls_by_status": self._get_calls_by_status(),
            "token_usage_by_service": self._get_token_usage_by_service()
        }
    
    def _get_calls_by_service(self) -> Dict[str, int]:
        """Count calls by service"""
        service_counts = defaultdict(int)
        for call in self.calls:
            service_counts[call.service] += 1
        return dict(service_counts)
    
    def _get_calls_by_status(self) -> Dict[str, int]:
        """Count calls by status"""
        status_counts = defaultdict(int)
        for call in self.calls:
            status_counts[call.status] += 1
        return dict(status_counts)
    
    def _get_token_usage_by_service(self) -> Dict[str, Dict[str, int]]:
        """Get token usage by service"""
        service_tokens = defaultdict(lambda: {"input": 0, "output": 0, "total": 0})
        for call in self.calls:
            service_tokens[call.service]["input"] += call.input_tokens
            service_tokens[call.service]["output"] += call.output_tokens
            service_tokens[call.service]["total"] += call.total_tokens
        return dict(service_tokens)
    
    def export_logs(self, filepath: str = None) -> str:
        """Export logs to a JSON file or return as a string"""
        log_data = []
        for call in self.calls:
            log_data.append({
                "timestamp": call.timestamp.isoformat(),
                "service": call.service,
                "endpoint": call.endpoint,
                "status": call.status,
                "duration": call.duration,
                "cost": call.cost,
                "input_tokens": call.input_tokens,
                "output_tokens": call.output_tokens,
                "total_tokens": call.total_tokens,
                "model": call.model,
                "prompt_size": call.prompt_size
            })
        
        export_data = {
            "logs": log_data,
            "summary": self.get_summary()
        }
        
        if filepath:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                json.dump(export_data, f, indent=2)
            return f"Logs exported to {filepath}"
        else:
            return json.dumps(export_data, indent=2)
    
    def reset(self):
        """Reset the tracker"""
        self.calls.clear()
        self.service_costs.clear()
        self.total_cost = 0.0
        self.total_tokens = 0
        self.total_input_tokens = 0
        self.total_output_tokens = 0