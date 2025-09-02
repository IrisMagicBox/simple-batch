import json
import time
import uuid
import random
from flask import Flask, request, jsonify
import logging

# --- 配置 ---
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

MODEL_NAME = "DeepSeek-V3"


def generate_mock_response(messages):
    """
    根据输入消息生成模拟的简短回复内容。
    回复长度为最后一条用户消息的 0.8 到 3 倍。
    """
    last_message_content = ""
    if messages and isinstance(messages, list):
        for msg in reversed(messages):
            if msg.get('role') == 'user':
                last_message_content = msg.get('content', '')
                break

    if not last_message_content:
        return "[Mock] Default reply."

    input_len = len(last_message_content)
    # 生成 0.8 到 3 倍长度的回复
    min_len = max(1, int(input_len * 0.8))
    max_len = max(min_len + 1, int(input_len * 3))

    # 简单模拟：截取或重复输入内容
    target_len = random.randint(min_len, max_len)

    if target_len <= input_len:
        # 如果目标长度小于等于输入，就截取
        mock_content = last_message_content[:target_len]
    else:
        # 如果目标长度大于输入，就重复
        repeat_times = (target_len // input_len) + 1
        mock_content = (last_message_content * repeat_times)[:target_len]

    # 简单添加前缀表示是模拟的
    prefix = "[Mock] "
    if target_len > len(prefix):
        mock_content = prefix + mock_content[len(prefix):]
    else:
        mock_content = prefix[:target_len] if target_len > 0 else ""

    return mock_content


@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """
    模拟 OpenAI 的 /v1/chat/completions 端点 (非流式)。
    """
    request_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created_time = int(time.time())

    # 1. 解析请求体
    try:
        data = request.get_json()
        if not data:
            logger.error("Invalid JSON in request body")
            return jsonify({"error": {"message": "Invalid JSON", "type": "invalid_request_error"}}), 400
    except Exception as e:
        logger.exception("Error parsing JSON")
        return jsonify({"error": {"message": f"Error parsing request: {e}", "type": "invalid_request_error"}}), 400

    logger.debug(f"Received request data: {data}")

    model = data.get("model", MODEL_NAME)
    messages = data.get("messages", [])
    # 忽略 stream 参数，始终返回非流式响应

    # 2. 生成模拟回复内容
    mock_content = generate_mock_response(messages)
    logger.info(f"Generated mock content (len={len(mock_content)}): {mock_content}")

    # 3. 构造并返回非流式响应
    logger.info("Non-streaming response requested")


    response_data = {
        "id": request_id,
        "object": "chat.completion",
        "created": created_time,
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": mock_content,
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": sum(len(msg.get('content', '')) for msg in messages),
            "completion_tokens": len(mock_content),
            "total_tokens": sum(len(msg.get('content', '')) for msg in messages) + len(mock_content)
        }
    }
    logger.debug(f"Sending non-streaming response: {response_data}")
    return jsonify(response_data)


# --- 主程序入口 ---
if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)
