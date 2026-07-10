#!/usr/bin/env python3
"""
全频谱协议 · 因果链报告生成器
从 ESS 推演结果生成结构化因果链报告
"""

import json
import time
import hashlib
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from .core.state import CivilizationState
from .engine.ess import ESSResult, ESSPath
from .governance.validator import DreamButterflyValidator
from .bridge.runestone import Runestone


@dataclass
class CausalChain:
    """因果链报告"""
    causal_chain_id: str
    timestamp: str
    version: str
    system_state: Dict
    ess_decision_context: Dict
    causal_paths: List[Dict]
    dream_butterfly_validation: Dict
    soul_account: Dict
    who_hurts: Dict
    frequency_plan: Dict
    full_chain_narrative: str


class ReportGenerator:
    """因果链报告生成器"""
    
    def __init__(self):
        self.version = "1.0"
    
    def generate(
        self,
        ess_result: ESSResult,
        dream_butterfly_result: Dict,
        state: CivilizationState,
        runestone: Runestone,
        selected_option: str,
        judgment_basis: List[str],
        system_state: str,
        spectrum_priority: str,
        timestamp: Optional[str] = None,
        causal_chain_id: Optional[str] = None
    ) -> Dict:
        """生成完整因果链报告"""
        timestamp = timestamp or time.strftime("%Y-%m-%dT%H:%M:%SZ")
        if causal_chain_id is None:
            state_payload = json.dumps({
                "survival": state.survival,
                "coordination": state.coordination,
                "meaning": state.meaning,
                "selected_option": selected_option,
                "system_state": system_state,
            }, sort_keys=True)
            state_digest = hashlib.sha256(state_payload.encode("utf-8")).hexdigest()[:8]
            causal_chain_id = f"CC-{time.strftime('%Y%m%d')}-{state_digest}"
        
        causal_chain = {
            "causal_chain_id": causal_chain_id,
            "timestamp": timestamp,
            "version": self.version,
            
            "system_state": {
                "current_state": system_state,
                "judgment_basis": judgment_basis,
                "spectrum_priority": spectrum_priority
            },
            
            "ess_decision_context": {
                "candidate_options": [p.option for p in ess_result.paths],
                "selected_option": selected_option,
                "horizon": ess_result.horizon
            },
            
            "causal_paths": self._build_causal_paths(ess_result),
            
            "dream_butterfly_validation": dream_butterfly_result,
            
            "soul_account": self._build_soul_account(state),
            
            "who_hurts": self._build_who_hurts(state),
            
            "frequency_plan": self._build_frequency_plan(state, system_state, spectrum_priority),
            
            "full_chain_narrative": self._build_narrative(state, ess_result, system_state)
        }
        
        return causal_chain
    
    def _build_causal_paths(self, ess_result: ESSResult) -> List[Dict]:
        paths = []
        for i, path in enumerate(ess_result.paths):
            paths.append({
                "path_id": path.option,
                "option": path.option,
                "selected": path.selected,
                "frequency_impacts": {
                    "低频": {
                        "seed_type": "生存保障" if path.low_freq_impact < 0.5 else "生存威胁",
                        "intensity": path.low_freq_impact,
                        "description": f"低频影响强度 {path.low_freq_impact:.2f}"
                    },
                    "中频": {
                        "seed_type": "信任修复" if path.mid_freq_impact < 0.5 else "信任侵蚀",
                        "intensity": path.mid_freq_impact,
                        "description": f"中频影响强度 {path.mid_freq_impact:.2f}"
                    },
                    "高频": {
                        "seed_type": "意义守护" if path.high_freq_impact > 0.5 else "意义漂移",
                        "intensity": path.high_freq_impact,
                        "description": f"高频影响强度 {path.high_freq_impact:.2f}"
                    }
                },
                "total_pain": path.total_pain,
                "chain_visual": f"低频({path.low_freq_impact:.2f}) → 中频({path.mid_freq_impact:.2f}) → 高频({path.high_freq_impact:.2f})"
            })
        return paths
    
    def _build_soul_account(self, state: CivilizationState) -> Dict:
        return {
            "initial_balance": 100,
            "debits": [
                {"item": "系统冲突误判", "points": -8, "basis": "误判为风险事件而非语义冲突"},
                {"item": "知情不作为", "points": -15, "basis": "已知风险但延迟行动"}
            ],
            "credits": [
                {"item": "公开承认", "points": +3, "basis": "公开承认跨系统语义冲突"}
            ],
            "balance": 80,
            "health_status": "亚健康"
        }
    
    def _build_who_hurts(self, state: CivilizationState) -> Dict:
        return {
            "低频": {"pain_bearer": "基层开发者", "description": "系统压力增加，生存成本上升"},
            "中频": {"pain_bearer": "合作伙伴", "description": "信任关系受损，协作成本上升"},
            "高频": {"pain_bearer": "决策者", "description": "意义方向模糊，长期叙事不确定"}
        }
    
    def _build_frequency_plan(self, state: CivilizationState, system_state: str, spectrum_priority: str) -> Dict:
        return {
            "recommendation": "优先修复中频信任，次低频生存，高频暂缓",
            "priority": spectrum_priority,
            "interventions": [
                {
                    "name": "信任重建机制",
                    "target_frequency": "中频",
                    "description": "建立跨系统信任审计机制",
                    "expected_effect": "信任资本+10分",
                    "urgency": "高"
                }
            ]
        }
    
    def _build_narrative(self, state: CivilizationState, ess_result: ESSResult, system_state: str) -> str:
        return f"本次决策推演识别到系统处于{system_state}状态。候选路径中，'{ess_result.selected_option}'的总痛苦最低，但需要持续监测系统状态变化。"
