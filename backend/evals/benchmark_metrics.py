from pydantic import BaseModel
from typing import List, Dict

class BenchmarkReport(BaseModel):
    total_cases: int = 0
    tp: int = 0  # True Positive
    tn: int = 0  # True Negative
    fp: int = 0  # False Positive
    fn: int = 0  # False Negative
    
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    far: float = 0.0  # False Acceptance Rate
    frr: float = 0.0  # False Rejection Rate

    def compute(self):
        total = self.tp + self.tn + self.fp + self.fn
        self.total_cases = total
        
        self.accuracy = ((self.tp + self.tn) / total) * 100.0 if total > 0 else 0.0
        self.precision = (self.tp / (self.tp + self.fp)) * 100.0 if (self.tp + self.fp) > 0 else 0.0
        self.recall = (self.tp / (self.tp + self.fn)) * 100.0 if (self.tp + self.fn) > 0 else 0.0
        
        prec_dec = self.precision / 100.0
        rec_dec = self.recall / 100.0
        
        if (prec_dec + rec_dec) > 0:
            self.f1_score = ((2 * prec_dec * rec_dec) / (prec_dec + rec_dec)) * 100.0
        else:
            self.f1_score = 0.0
        
        actual_negatives = self.fp + self.tn
        actual_positives = self.fn + self.tp
        self.far = (self.fp / actual_negatives) * 100.0 if actual_negatives > 0 else 0.0
        self.frr = (self.fn / actual_positives) * 100.0 if actual_positives > 0 else 0.0