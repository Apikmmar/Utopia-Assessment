import json
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError, ConnectTimeoutError, ReadTimeoutError
from core import config
from modules.ai.constants import (
    ANSWER_MAX_LENGTH, CONNECT_TIMEOUT_SECONDS, ERROR_MESSAGE_MAX_LENGTH, INVOCATION_ERROR, INVOCATION_TIMEOUT, MAX_OUTPUT_TOKENS,
    READ_TIMEOUT_SECONDS, SYSTEM_PROMPT,
)

COMPLETE_STOP_REASONS = ("end_turn", "stop_sequence")
_client = {}


class ProviderError(Exception):
    # Carries the invocation status, a sanitized reason, and any token usage the provider reported.
    def __init__(self, status, reason, usage=None):
        super().__init__(reason)
        self.status = status
        self.reason = reason[:ERROR_MESSAGE_MAX_LENGTH]
        self.usage = usage


class BedrockProvider:
    # Wraps one Bedrock runtime client and the model id it calls.
    def __init__(self, client, modelId):
        self.client = client
        self.modelId = modelId

    # Asks the model for a plain-text summary of the facts in one non-streaming call and returns {text, usage}.
    # Raises ProviderError for a timeout, a refusal, or an empty, cut-off, or oversized answer.
    def summarize(self, facts):
        try:
            response = self.client.converse(
                modelId=self.modelId,
                system=[{"text": SYSTEM_PROMPT}],
                messages=[{"role": "user", "content": [{"text": json.dumps(facts, separators=(",", ":"), default=str)}]}],
                inferenceConfig={"maxTokens": MAX_OUTPUT_TOKENS, "temperature": 0},
            )
        except (ConnectTimeoutError, ReadTimeoutError) as error:
            raise ProviderError(INVOCATION_TIMEOUT, type(error).__name__) from None
        except ClientError as error:
            raise ProviderError(INVOCATION_ERROR, error.response.get("Error", {}).get("Code") or type(error).__name__) from None
        except BotoCoreError as error:
            raise ProviderError(INVOCATION_ERROR, type(error).__name__) from None
        return readAnswer(response)

    # Closes the HTTP connections the client holds.
    def close(self):
        self.client.close()

# Returns {text, usage} from a Converse response, raising ProviderError unless it is a complete, nonempty text
# answer within the length limit.
def readAnswer(response):
    usage = readUsage(response.get("usage"))
    if response.get("stopReason") not in COMPLETE_STOP_REASONS:
        raise ProviderError(INVOCATION_ERROR, f"StopReason:{response.get('stopReason')}", usage)
    content = (((response.get("output") or {}).get("message") or {}).get("content")) or []
    text = "".join(part.get("text", "") for part in content if isinstance(part, dict)).strip()
    if not text:
        raise ProviderError(INVOCATION_ERROR, "EmptyAnswer", usage)
    if len(text) > ANSWER_MAX_LENGTH:
        raise ProviderError(INVOCATION_ERROR, "AnswerTooLong", usage)
    return {"text": text, "usage": usage}

# Returns the token counts a response reported, or None when it reported none.
def readUsage(usage):
    if not usage:
        return None
    inputTokens, outputTokens = int(usage.get("inputTokens") or 0), int(usage.get("outputTokens") or 0)
    return {"input": inputTokens, "output": outputTokens, "total": int(usage.get("totalTokens") or inputTokens + outputTokens)}

# Returns the shared Bedrock provider, creating its client on first use with short timeouts and no retries.
def getProvider():
    if "provider" not in _client:
        clientConfig = Config(
            connect_timeout=CONNECT_TIMEOUT_SECONDS, read_timeout=READ_TIMEOUT_SECONDS, retries={"total_max_attempts": 1, "mode": "standard"},
        )
        client = boto3.client("bedrock-runtime", region_name=config.awsRegion(), config=clientConfig)
        _client["provider"] = BedrockProvider(client, config.aiBedrockModelId())
    return _client["provider"]

# Closes the shared provider's client at shutdown, if one was created.
def closeProvider():
    provider = _client.pop("provider", None)
    if provider is not None:
        provider.close()


__all__ = ["BedrockProvider", "ProviderError", "closeProvider", "getProvider", "readAnswer"]
