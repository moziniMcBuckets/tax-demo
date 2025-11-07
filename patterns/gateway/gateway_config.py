"""AgentCore Gateway configuration with Lambda target"""

GATEWAY_CONFIG = {
    "gateway_name": "basic-gateway",
    "targets": [
        {
            "target_id": "sample-tool",
            "target_type": "LAMBDA",
            "auth_type": "IAM_ROLE"
        }
    ]
}
