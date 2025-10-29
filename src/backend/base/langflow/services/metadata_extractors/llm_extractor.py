"""LLM组件元数据提取器

专门用于LLM模型组件（OpenAI, Anthropic, Groq等）的元数据提取。
提取Token消耗、成本、模型参数等LLM特定信息。
"""

from loguru import logger

from langflow.services.metadata_extractors.base import BaseMetadataExtractor


class LLMMetadataExtractor(BaseMetadataExtractor):
    """LLM组件元数据提取器

    提取LLM相关的元数据：
    - 模型名称和参数
    - Token消耗（prompt_tokens, completion_tokens）
    - API调用成本
    - 响应质量指标
    """

    async def extract_input_metadata(self) -> dict:
        """提取输入元信息（LLM特定）

        Returns:
            输入元信息字典，包含：
            - model_info: 模型名称、参数配置
            - prompt_info: Prompt相关信息
        """
        metadata = {}

        # 提取模型信息
        model_info = self._extract_model_info()
        if model_info:
            metadata["model_info"] = model_info

        # 提取Prompt信息
        prompt_info = self._extract_prompt_info()
        if prompt_info:
            metadata["prompt_info"] = prompt_info

        return metadata

    async def extract_output_metadata(
        self,
        results: dict | None = None,
        artifacts: dict | None = None,
    ) -> dict:
        """提取输出元信息（LLM特定）

        Args:
            results: 组件执行结果
            artifacts: 组件产生的artifacts

        Returns:
            输出元信息字典，包含：
            - llm_metrics: Token消耗、成本等指标
            - response_info: 响应内容信息
        """
        metadata = {}

        # 提取LLM指标
        if results or artifacts:
            llm_metrics = self._extract_llm_metrics(results, artifacts)
            if llm_metrics:
                metadata["llm_metrics"] = llm_metrics

        return metadata

    def _extract_model_info(self) -> dict | None:
        """提取模型信息

        Returns:
            模型信息字典，例如：
            {
                "model_name": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 1000,
            }
        """
        if not self.vertex.params:
            return None

        model_info = {}

        # 模型名称
        for key in ["model_name", "model", "model_id"]:
            if key in self.vertex.params:
                value = self.vertex.params[key]
                model_info["model_name"] = getattr(value, "value", str(value)) if hasattr(value, "value") else str(value)
                break

        # 温度参数
        if "temperature" in self.vertex.params:
            temp = self.vertex.params["temperature"]
            try:
                model_info["temperature"] = float(getattr(temp, "value", temp) if hasattr(temp, "value") else temp)
            except (ValueError, TypeError):
                pass

        # 最大tokens
        if "max_tokens" in self.vertex.params:
            max_tok = self.vertex.params["max_tokens"]
            try:
                model_info["max_tokens"] = int(getattr(max_tok, "value", max_tok) if hasattr(max_tok, "value") else max_tok)
            except (ValueError, TypeError):
                pass

        return model_info if model_info else None

    def _extract_prompt_info(self) -> dict | None:
        """提取Prompt信息

        Returns:
            Prompt信息字典
        """
        if not self.vertex.params:
            return None

        prompt_info = {}

        # Prompt文本
        for key in ["input_value", "prompt", "message", "query"]:
            if key in self.vertex.params:
                value = self.vertex.params[key]
                prompt_text = getattr(value, "value", str(value)) if hasattr(value, "value") else str(value)
                prompt_info["prompt_length"] = len(prompt_text)
                # 不存储完整prompt，只存储长度（隐私考虑）
                break

        return prompt_info if prompt_info else None

    def _extract_llm_metrics(self, results: dict | None, artifacts: dict | None) -> dict | None:
        """提取LLM指标（Token消耗、成本等）

        Args:
            results: 组件执行结果
            artifacts: 组件产生的artifacts

        Returns:
            LLM指标字典，例如：
            {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
                "estimated_cost_usd": 0.003,
            }
        """
        metrics = {}

        try:
            # 从results中提取token信息
            if results:
                # 尝试从message对象中提取
                for key in ["message", "result", "output"]:
                    if key in results:
                        msg = results[key]
                        # 检查是否有usage_metadata
                        if hasattr(msg, "usage_metadata"):
                            usage = msg.usage_metadata
                            if hasattr(usage, "input_tokens"):
                                metrics["prompt_tokens"] = usage.input_tokens
                            if hasattr(usage, "output_tokens"):
                                metrics["completion_tokens"] = usage.output_tokens
                            if hasattr(usage, "total_tokens"):
                                metrics["total_tokens"] = usage.total_tokens
                        break

            # 从artifacts中提取token信息
            if artifacts and "message" in artifacts:
                for msg_artifact in artifacts["message"]:
                    if hasattr(msg_artifact, "usage_metadata"):
                        usage = msg_artifact.usage_metadata
                        if hasattr(usage, "input_tokens"):
                            metrics["prompt_tokens"] = usage.input_tokens
                        if hasattr(usage, "output_tokens"):
                            metrics["completion_tokens"] = usage.output_tokens
                        if hasattr(usage, "total_tokens"):
                            metrics["total_tokens"] = usage.total_tokens
                        break

            # 计算估算成本（简化版本）
            if "total_tokens" in metrics:
                # TODO: 使用实际的模型定价
                # 这里使用GPT-4的粗略估算：$0.03/1K prompt tokens, $0.06/1K completion tokens
                prompt_cost = metrics.get("prompt_tokens", 0) * 0.00003
                completion_cost = metrics.get("completion_tokens", 0) * 0.00006
                metrics["estimated_cost_usd"] = round(prompt_cost + completion_cost, 6)

        except Exception as e:
            logger.warning(f"Failed to extract LLM metrics: {e}")

        return metrics if metrics else None
