#!/usr/bin/env python3
"""
全频谱协议 · 样本转GBrain知识图谱脚本
将25家高置信度种子样本转换为GBrain可导入的JSON格式
"""

import json
import os
from typing import Dict, List, Any, Optional


# 25家高置信度种子样本数据
SEED_SAMPLES = [
    # 国家样本
    {"name": "中国", "type": "country", "e_subtype": "E-2a-I", "gtm": "大国-稳",
     "l_score": 0.85, "m_score": 0.75, "h_score": 0.80,
     "production": "工业+数字+AI混合态", "time_layer": "中华人民共和国", "circle": "中华"},
    {"name": "美国", "type": "country", "e_subtype": "E-2b", "gtm": "大国-塌",
     "l_score": 0.45, "m_score": 0.20, "h_score": 0.60,
     "production": "数字+AI混合态", "time_layer": "数字-智能时代", "circle": "西方"},
    {"name": "日本", "type": "country", "e_subtype": "E-2c", "gtm": "大国-衰",
     "l_score": 0.35, "m_score": 0.55, "h_score": 0.40,
     "production": "数字+工业混合态", "time_layer": "现代", "circle": "中华"},
    {"name": "欧盟", "type": "country", "e_subtype": "E-2d-I", "gtm": "大国-碎-I",
     "l_score": 0.50, "m_score": 0.45, "h_score": 0.50,
     "production": "数字+工业混合态", "time_layer": "数字-智能时代", "circle": "西方"},
    {"name": "印度", "type": "country", "e_subtype": "E-2a-IIa", "gtm": "大国-起-I",
     "l_score": 0.70, "m_score": 0.50, "h_score": 0.60,
     "production": "数字+工业混合态", "time_layer": "现代印度", "circle": "南亚"},
    {"name": "越南", "type": "country", "e_subtype": "E-2a-IIb", "gtm": "大国-起-II",
     "l_score": 0.80, "m_score": 0.70, "h_score": 0.65,
     "production": "工业+数字混合态", "time_layer": "现代", "circle": "中华"},
    {"name": "墨西哥", "type": "country", "e_subtype": "E-2d-II", "gtm": "大国-碎-II",
     "l_score": 0.35, "m_score": 0.45, "h_score": 0.50,
     "production": "工业+数字混合态", "time_layer": "21世纪", "circle": "拉美"},
    {"name": "沙特", "type": "country", "e_subtype": "E-2e", "gtm": "大国-起-III",
     "l_score": 0.70, "m_score": 0.50, "h_score": 0.65,
     "production": "AI转型期", "time_layer": "后石油时代", "circle": "伊斯兰"},
    {"name": "尼日利亚", "type": "country", "e_subtype": "E-2d-III", "gtm": "大国-碎-III",
     "l_score": 0.40, "m_score": 0.25, "h_score": 0.55,
     "production": "工业+石油混合态", "time_layer": "21世纪", "circle": "非洲"},
    {"name": "巴西", "type": "country", "e_subtype": "E-2d-IV", "gtm": "大国-碎-IV",
     "l_score": 0.45, "m_score": 0.45, "h_score": 0.50,
     "production": "工业+大宗商品", "time_layer": "21世纪", "circle": "拉美"},
    {"name": "俄罗斯", "type": "country", "e_subtype": "E-2f", "gtm": "大国-威权-I",
     "l_score": 0.50, "m_score": 0.25, "h_score": 0.45,
     "production": "工业+AI混合态", "time_layer": "现代", "circle": "西方"},
    # 企业样本
    {"name": "中通", "type": "enterprise", "gene": "加盟物流型", "gtm": "防御型",
     "l_score": 0.80, "m_score": 0.55, "h_score": 0.50,
     "production": "工业+数字混合态", "time_layer": "中华人民共和国", "circle": "中华"},
    {"name": "京东", "type": "enterprise", "gene": "直营零售型", "gtm": "防御型",
     "l_score": 0.70, "m_score": 0.50, "h_score": 0.50,
     "production": "数字+工业混合态", "time_layer": "中华人民共和国", "circle": "中华"},
    {"name": "联想", "type": "enterprise", "gene": "OEM转型型-A", "gtm": "防御型",
     "l_score": 0.75, "m_score": 0.50, "h_score": 0.60,
     "production": "数字+工业混合态", "time_layer": "中华人民共和国", "circle": "中华"},
    {"name": "海信", "type": "enterprise", "gene": "OEM转型型-B", "gtm": "防御型",
     "l_score": 0.55, "m_score": 0.50, "h_score": 0.55,
     "production": "工业+数字混合态", "time_layer": "中华人民共和国", "circle": "中华"},
    {"name": "中石化", "type": "enterprise", "gene": "产业周期裹挟型", "gtm": "防御型",
     "l_score": 0.45, "m_score": 0.50, "h_score": 0.45,
     "production": "工业+AI混合态", "time_layer": "中华人民共和国", "circle": "中华"},
    {"name": "美团", "type": "enterprise", "gene": "平台型-多边", "gtm": "防御型",
     "l_score": 0.45, "m_score": 0.50, "h_score": 0.55,
     "production": "数字+AI混合态", "time_layer": "中华人民共和国", "circle": "中华"},
    {"name": "宁德时代", "type": "enterprise", "gene": "制造型-制霸", "gtm": "保养型",
     "l_score": 0.85, "m_score": 0.50, "h_score": 0.80,
     "production": "工业+AI混合态", "time_layer": "中华人民共和国", "circle": "中华"},
    {"name": "台积电", "type": "enterprise", "gene": "制造型-制霸", "gtm": "保养型",
     "l_score": 0.85, "m_score": 0.50, "h_score": 0.85,
     "production": "AI+工业混合态", "time_layer": "现代", "circle": "中华"},
    {"name": "OpenAI", "type": "enterprise", "gene": "平台型-技霸-崩塌", "gtm": "抢救型",
     "l_score": 0.20, "m_score": 0.10, "h_score": 0.60,
     "production": "AI核心层", "time_layer": "数字-智能时代", "circle": "西方"},
    {"name": "Anthropic", "type": "enterprise", "gene": "平台型-技霸-裂缝", "gtm": "预防型",
     "l_score": 0.50, "m_score": 0.45, "h_score": 0.65,
     "production": "AI核心层", "time_layer": "数字-智能时代", "circle": "西方"},
    {"name": "Google", "type": "enterprise", "gene": "平台型-技霸-制霸-上市", "gtm": "保养型",
     "l_score": 0.90, "m_score": 0.50, "h_score": 0.85,
     "production": "数字+AI混合态", "time_layer": "数字-智能时代", "circle": "西方"},
    {"name": "字节跳动", "type": "enterprise", "gene": "平台型-技霸-制霸-非上市中国", "gtm": "预防+保养混合",
     "l_score": 0.65, "m_score": 0.50, "h_score": 0.70,
     "production": "数字+AI混合态", "time_layer": "中华人民共和国", "circle": "中华"},
    {"name": "亚马逊", "type": "enterprise", "gene": "平台型-多边", "gtm": "企业-重构型",
     "l_score": 0.80, "m_score": 0.50, "h_score": 0.70,
     "production": "数字+AI混合态", "time_layer": "数字-智能时代", "circle": "西方"},
    {"name": "越南电子代工", "type": "enterprise", "gene": "制造型-制霸代工", "gtm": "—",
     "l_score": 0.65, "m_score": 0.50, "h_score": 0.60,
     "production": "工业+数字混合态", "time_layer": "现代", "circle": "中华"},
]


def convert_sample_to_gbrain(sample: Dict) -> Dict:
    """将单个样本转换为GBrain格式"""
    entity_type_map = {
        "country": "country",
        "enterprise": "enterprise"
    }
    
    entity = {
        "name": sample["name"],
        "entity_type": entity_type_map.get(sample.get("type"), "unknown"),
        "description": f"{sample.get('gene', sample.get('e_subtype', 'unknown'))} / {sample.get('gtm', 'unknown')}",
        "properties": {
            "l_freq_score": sample.get("l_score", 0.5),
            "m_freq_score": sample.get("m_score", 0.5),
            "h_freq_score": sample.get("h_score", 0.5),
            "production_structure": sample.get("production", "unknown"),
            "time_layer": sample.get("time_layer", "unknown"),
            "circle": sample.get("circle", "unknown"),
            "confidence": "high"
        }
    }
    
    # 添加基因类型或E子型
    if "gene" in sample:
        entity["properties"]["gene_type"] = sample["gene"]
    if "e_subtype" in sample:
        entity["properties"]["e_subtype"] = sample["e_subtype"]
    if "gtm" in sample:
        entity["properties"]["gtm_tier"] = sample["gtm"]
    
    return entity


def convert_all_samples(samples: List[Dict]) -> Dict:
    """转换所有样本"""
    entities = []
    for sample in samples:
        try:
            entity = convert_sample_to_gbrain(sample)
            entities.append(entity)
        except Exception as e:
            print(f"⚠️ 转换失败: {sample.get('name', 'unknown')} - {e}")
    
    return {
        "entities": entities,
        "relations": []
    }


def main():
    """主函数"""
    print("=" * 60)
    print("全频谱协议 · 样本转GBrain知识图谱")
    print("=" * 60)
    
    # 转换
    output = convert_all_samples(SEED_SAMPLES)
    
    # 输出文件
    output_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "knowledge-graph",
        "gbrain_import_25_samples.json"
    )
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 已生成 {len(output['entities'])} 个节点")
    print(f"📁 文件路径: {output_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
