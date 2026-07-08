#!/bin/bash
# ============================================================
# Full Spectrum Engine v0.5-alpha REST API — curl 示例
#
# 前提：先启动 API 服务
#   pip install -e ".[api]"
#   python -m src.api.server
#
# 服务默认运行在 http://127.0.0.1:8000
# API 文档: http://127.0.0.1:8000/docs
# ============================================================

BASE_URL="http://127.0.0.1:8000"

echo "=========================================="
echo "1. 健康检查"
echo "=========================================="
curl -s "${BASE_URL}/api/v1/health" | python -m json.tool
echo ""

echo "=========================================="
echo "2. 仿真评估 — 直接模式（scenario dict）"
echo "=========================================="
curl -s -X POST "${BASE_URL}/api/v1/evaluate" \
  -H "Content-Type: application/json" \
  -d "{
    \"scenario\": {
      \"simulation_id\": \"API_DEMO_DIRECT\",
      \"input_query\": \"API direct mode test\",
      \"sensitivity_level\": \"high\",
      \"enterprise_id\": \"api-demo\",
      \"rule_version\": \"v0.3\",
      \"initial_state\": {\"survival\": 0.72, \"coordination\": 0.45, \"meaning\": 0.55},
      \"weights\": {\"survival\": 0.40, \"coordination\": 0.35, \"meaning\": 0.25},
      \"ess_horizon\": 5,
      \"ess_candidates\": 10,
      \"conflict_density\": 0.6,
      \"irreversibility\": 0.4,
      \"diffusivity\": 0.5
    },
    \"seed\": 42
  }" | python -m json.tool
echo ""

echo "=========================================="
echo "3. 仿真评估 — 适配器模式（industry + metrics）"
echo "=========================================="
curl -s -X POST "${BASE_URL}/api/v1/evaluate" \
  -H "Content-Type: application/json" \
  -d "{
    \"industry\": \"ecommerce_customer_service\",
    \"metrics\": {
      \"refund_rate\": 0.15,
      \"complaint_rate\": 0.12,
      \"promise_conflict_rate\": 0.22,
      \"knowledge_source_conflict_rate\": 0.18,
      \"manual_handoff_rate\": 0.28,
      \"appeal_success_rate\": 0.25,
      \"resolution_satisfaction\": 0.48,
      \"response_time_score\": 0.62,
      \"policy_clarity_score\": 0.45
    },
    \"seed\": 42,
    \"include_input_metrics\": false
  }" | python -m json.tool
echo ""

echo "=========================================="
echo "4. 符石生成"
echo "=========================================="
curl -s -X POST "${BASE_URL}/api/v1/runestone" \
  -H "Content-Type: application/json" \
  -d "{
    \"decision\": \"W3\",
    \"reason\": {\"enterprise_id\": \"api-demo\", \"rule_version\": \"v0.3\"},
    \"risk_vector\": {
      \"survival_impact\": 0.3,
      \"trust_impact\": 0.5,
      \"meaning_impact\": 0.2,
      \"reversibility\": 0.6,
      \"explainability\": 0.8,
      \"diffusivity\": 0.4,
      \"urgency\": 0.3,
      \"uncertainty\": 0.2
    },
    \"seed\": 42
  }" | python -m json.tool
echo ""

echo "=========================================="
echo "5. 决策查询（需要先执行 evaluate 获取 decision_id）"
echo "=========================================="
# 先 evaluate 获取 decision_id
DECISION_ID=$(curl -s -X POST "${BASE_URL}/api/v1/evaluate" \
  -H "Content-Type: application/json" \
  -d "{
    \"scenario\": {
      \"simulation_id\": \"API_DEMO_LOOKUP\",
      \"initial_state\": {\"survival\": 0.72, \"coordination\": 0.45, \"meaning\": 0.55},
      \"irreversibility\": 0.4,
      \"diffusivity\": 0.5
    },
    \"seed\": 42
  }" -D - 2>/dev/null | grep -i "x-decision-id" | awk '{print $2}' | tr -d '\r\n')

echo "Decision ID: ${DECISION_ID}"
curl -s "${BASE_URL}/api/v1/decisions/${DECISION_ID}" | python -m json.tool
echo ""

echo "=========================================="
echo "6. 查看响应头（元信息）"
echo "=========================================="
curl -s -I "${BASE_URL}/api/v1/health" 2>/dev/null | grep -i "x-"
echo ""

echo "=========================================="
echo "7. 错误处理示例"
echo "=========================================="
echo "--- 未注册适配器 (422) ---"
curl -s -X POST "${BASE_URL}/api/v1/evaluate" \
  -H "Content-Type: application/json" \
  -d '{"industry": "nonexistent", "metrics": {}, "seed": 42}' | python -m json.tool
echo ""

echo "--- 不存在的决策 (404) ---"
curl -s "${BASE_URL}/api/v1/decisions/DEC_NONEXISTENT" | python -m json.tool
echo ""

echo "Done."
