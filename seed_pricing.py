#!/usr/bin/env python3
"""
Скрипт для заполнения таблицы model_pricing актуальными ценами
из каталога KodikRouter (цены в рублях за 1M токенов).
Запуск: python3 seed_pricing.py
"""
import asyncio
from sqlalchemy import select
from app.database import get_session, engine
from app.models import Base, ModelPricing

PRICING = [
    # (model_id, input_rub_per_1m, output_rub_per_1m)

    # ── AI21 ──────────────────────────────────────────────────────────────────
    ("ai21/jamba-large-1.7", 149.0, 597.0),

    # ── Aion Labs ─────────────────────────────────────────────────────────────
    ("aion-labs/aion-1.0", 299.0, 597.0),
    ("aion-labs/aion-1.0-mini", 52.0, 105.0),
    ("aion-labs/aion-2.0", 60.0, 119.0),
    ("aion-labs/aion-rp-1.0", 60.0, 119.0),

    # ── AlfredPros ────────────────────────────────────────────────────────────
    ("alfredpros/codellama-7b-instruct-solidity", 60.0, 90.0),

    # ── AllenAI ───────────────────────────────────────────────────────────────
    ("allenai/olmo-3-32b-think", 11.0, 37.0),

    # ── Amazon ────────────────────────────────────────────────────────────────
    ("amazon/nova-2-lite", 22.0, 187.0),
    ("amazon/nova-lite-1.0", 4.48, 18.0),
    ("amazon/nova-micro-1.0", 2.61, 10.0),
    ("amazon/nova-premier-1.0", 187.0, 933.0),
    ("amazon/nova-pro-1.0", 60.0, 239.0),

    # ── Anthropic ─────────────────────────────────────────────────────────────
    ("anthropic/claude-haiku-latest", 75.0, 373.0),
    ("anthropic/claude-sonnet-latest", 224.0, 1120.0),
    ("anthropic/claude-3-haiku", 19.0, 93.0),
    ("anthropic/claude-3.5-haiku", 60.0, 299.0),
    ("anthropic/claude-3.7-sonnet", 224.0, 1120.0),
    ("anthropic/claude-3.7-sonnet-thinking", 224.0, 1120.0),
    ("anthropic/claude-haiku-4.5", 75.0, 373.0),
    ("anthropic/claude-opus-4", 1120.0, 5600.0),
    ("anthropic/claude-opus-4.1", 1120.0, 5600.0),
    ("anthropic/claude-opus-4.5", 373.0, 1867.0),
    ("anthropic/claude-sonnet-4", 224.0, 1120.0),
    ("anthropic/claude-sonnet-4.5", 224.0, 1120.0),

    # ── Arcee AI ──────────────────────────────────────────────────────────────
    ("arcee-ai/coder-large", 37.0, 60.0),
    ("arcee-ai/maestro-reasoning", 67.0, 246.0),
    ("arcee-ai/spotlight", 13.0, 13.0),
    ("arcee-ai/trinity-large-preview", 11.0, 34.0),
    ("arcee-ai/trinity-large-thinking", 16.0, 63.0),
    ("arcee-ai/trinity-large-thinking-free", 0.0, 0.0),
    ("arcee-ai/trinity-mini", 3.36, 11.0),
    ("arcee-ai/virtuoso-large", 56.0, 90.0),

    # ── BAAI ──────────────────────────────────────────────────────────────────
    ("baai/bge-base-en-v1.5", 0.373, 0.0),
    ("baai/bge-large-en-v1.5", 0.747, 0.0),
    ("baai/bge-m3", 0.747, 0.0),

    # ── Baidu ─────────────────────────────────────────────────────────────────
    ("baidu/qianfan-cobuddy-free", 0.0, 0.0),
    ("baidu/ernie-4.5-21b-a3b", 5.23, 21.0),
    ("baidu/ernie-4.5-21b-a3b-thinking", 5.23, 21.0),
    ("baidu/ernie-4.5-300b-a47b", 21.0, 82.0),
    ("baidu/ernie-4.5-vl-28b-a3b", 10.0, 42.0),
    ("baidu/ernie-4.5-vl-424b-a47b", 31.0, 93.0),
    ("baidu/qianfan-ocr-fast", 51.0, 210.0),
    ("baidu/qianfan-ocr-fast-free", 0.0, 0.0),

    # ── ByteDance ─────────────────────────────────────────────────────────────
    ("bytedance/ui-tars-7b", 7.47, 15.0),
    ("bytedance-seed/seed-1.6", 19.0, 149.0),
    ("bytedance-seed/seed-1.6-flash", 5.60, 22.0),
    ("bytedance-seed/seed-2.0-lite", 19.0, 149.0),
    ("bytedance-seed/seed-2.0-mini", 7.47, 30.0),

    # ── KodikRouter ───────────────────────────────────────────────────────────
    ("kodikrouter/free", 0.0, 0.0),

    # ── Cohere ────────────────────────────────────────────────────────────────
    ("cohere/command-a", 187.0, 747.0),
    ("cohere/command-r-08-2024", 11.0, 45.0),
    ("cohere/command-r-plus-08-2024", 187.0, 747.0),
    ("cohere/command-r7b-12-2024", 2.80, 11.0),

    # ── Deep Cogito ───────────────────────────────────────────────────────────
    ("deepcogito/cogito-v2.1-671b", 93.0, 93.0),

    # ── DeepSeek ──────────────────────────────────────────────────────────────
    ("deepseek/deepseek-v3", 24.0, 66.0),
    ("deepseek/deepseek-v3-0324", 15.0, 57.0),
    ("deepseek/deepseek-v3.1", 16.0, 59.0),
    ("deepseek/deepseek-v3.1-terminus", 20.0, 71.0),
    ("deepseek/deepseek-v3.2", 19.0, 28.0),
    ("deepseek/deepseek-v3.2-exp", 20.0, 31.0),
    ("deepseek/deepseek-v3.2-speciale", 21.0, 32.0),
    ("deepseek/deepseek-v4-flash", 8.36, 17.0),
    ("deepseek/deepseek-v4-flash-free", 0.0, 0.0),
    ("deepseek/deepseek-v4-pro", 32.0, 65.0),
    ("deepseek/deepseek-r1", 52.0, 187.0),
    ("deepseek/deepseek-r1-0528", 37.0, 161.0),
    ("deepseek/deepseek-r1-distill-qwen-32b", 22.0, 22.0),

    # ── EssentialAI ───────────────────────────────────────────────────────────
    ("essentialai/rnj-1-instruct", 11.0, 11.0),

    # ── Alpindale ─────────────────────────────────────────────────────────────
    ("alpindale/goliath-120b", 280.0, 560.0),

    # ── Google ────────────────────────────────────────────────────────────────
    ("google/gemini-flash-latest", 37.0, 224.0),
    ("google/gemini-pro-latest", 149.0, 896.0),
    ("google/gemini-2.0-flash", 7.47, 30.0),
    ("google/gemini-2.0-flash-lite", 5.60, 22.0),
    ("google/gemini-2.5-flash", 22.0, 187.0),
    ("google/gemini-2.5-flash-lite", 7.47, 30.0),
    ("google/gemini-2.5-flash-lite-preview-09-2025", 7.47, 30.0),
    ("google/gemini-2.5-pro", 93.0, 747.0),
    ("google/gemini-2.5-pro-preview-05-06", 93.0, 747.0),
    ("google/gemma-2-27b", 49.0, 49.0),
    ("google/gemma-3-12b", 2.99, 9.71),
    ("google/gemma-3-27b", 5.97, 12.0),
    ("google/gemma-3-4b", 2.99, 5.97),
    ("google/gemma-3n-4b", 4.48, 8.96),
    ("google/gemma-4-26b-a4b", 4.48, 25.0),
    ("google/gemma-4-26b-a4b-free", 0.0, 0.0),
    ("google/gemma-4-31b", 8.96, 28.0),
    ("google/gemma-4-31b-free", 0.0, 0.0),
    ("google/gemini-embedding-001", 11.0, 0.0),
    ("google/gemini-embedding-2-preview", 15.0, 0.0),

    # ── IBM Granite ───────────────────────────────────────────────────────────
    ("ibm-granite/granite-4.0-micro", 1.27, 8.36),

    # ── MiniMax ───────────────────────────────────────────────────────────────
    ("minimax/minimax-m1", 30.0, 164.0),
    ("minimax/minimax-m2", 19.0, 75.0),
    ("minimax/minimax-m2.1", 22.0, 71.0),
    ("minimax/minimax-m2.5", 11.0, 86.0),
    ("minimax/minimax-m2.5-free", 0.0, 0.0),
    ("minimax/minimax-01", 15.0, 82.0),

    # ── Mistral ───────────────────────────────────────────────────────────────
    ("mistral/mistral-large", 149.0, 447.0),
    ("mistral/mistral-large-2407", 149.0, 447.0),
    ("mistral/mistral-large-2411", 149.0, 447.0),
    ("mistral/codestral-2508", 22.0, 67.0),
    ("mistral/devstral-small-1.1", 7.45, 22.0),
    ("mistral/ministral-3b-2410", 7.45, 7.45),
    ("mistral/ministral-8b-2410", 11.0, 11.0),
    ("mistral/mistral-7b-instruct-v0.1", 8.20, 14.0),
    ("mistral/mistral-embed-2312", 7.45, 0.0),
    ("mistral/mistral-large-2412", 37.0, 112.0),
    ("mistral/mistral-medium-3", 30.0, 149.0),
    ("mistral/mistral-nemo", 1.49, 2.24),
    ("mistral/mistral-small-3.1-24b", 3.73, 5.96),
    ("mistral/mistral-small-3.2-24b", 5.59, 15.0),
    ("mistral/mixtral-8x22b-instruct", 149.0, 447.0),
    ("mistral/pixtral-large-2411", 149.0, 447.0),
    ("mistral/saba", 15.0, 45.0),

    # ── MoonshotAI ────────────────────────────────────────────────────────────
    ("moonshotai/kimi-k2-0711", 42.0, 171.0),
    ("moonshotai/kimi-k2-thinking", 45.0, 186.0),

    # ── Morph ─────────────────────────────────────────────────────────────────
    ("morph/morph-v3-fast", 60.0, 89.0),
    ("morph/morph-v3-large", 67.0, 142.0),

    # ── Gryphe ────────────────────────────────────────────────────────────────
    ("gryphe/mythomax-13b", 4.47, 4.47),

    # ── Nous Research ─────────────────────────────────────────────────────────
    ("nousresearch/hermes-3-405b-instruct", 15.0, 45.0),

    # ── Meta ──────────────────────────────────────────────────────────────────
    ("meta-llama/llama-3.1-405b-instruct", 149.0, 447.0),
    ("meta-llama/llama-3.1-70b-instruct", 37.0, 112.0),
    ("meta-llama/llama-3.1-8b-instruct", 7.45, 7.45),
    ("meta-llama/llama-3.2-11b-vision-instruct", 7.45, 7.45),
    ("meta-llama/llama-3.2-1b-instruct", 2.24, 2.24),
    ("meta-llama/llama-3.2-3b-instruct", 3.73, 3.73),
    ("meta-llama/llama-3.2-90b-vision-instruct", 149.0, 447.0),
    ("meta-llama/llama-3.3-70b-instruct", 37.0, 112.0),
    ("meta-llama/llama-4-maverick", 15.0, 59.0),
    ("meta-llama/llama-4-scout", 7.45, 22.0),
    ("meta-llama/llama-guard-4-12b", 7.45, 7.45),

    # ── Microsoft ─────────────────────────────────────────────────────────────
    ("microsoft/mai-ds-r1", 52.0, 187.0),
    ("microsoft/phi-4", 22.0, 66.0),
    ("microsoft/phi-4-14b-mini-instruct", 7.45, 22.0),
    ("microsoft/phi-4-multimodal-instruct", 22.0, 66.0),
    ("microsoft/phi-4-reasoning", 37.0, 112.0),
    ("microsoft/phi-4-reasoning-plus", 37.0, 112.0),
    ("microsoft/wizardlm-2-8x22b", 89.0, 269.0),

    # ── Nebius ────────────────────────────────────────────────────────────────
    ("nebius/nebius-0.1-70b", 37.0, 112.0),
    ("nebius/nebius-0.1-8b", 7.45, 7.45),

    # ── NVIDIA ────────────────────────────────────────────────────────────────
    ("nvidia/llama-3.1-nemotron-ultra-253b-v1", 89.0, 269.0),
    ("nvidia/llama-3.1-nemotron-70b-instruct", 37.0, 112.0),

    # ── OpenAI ────────────────────────────────────────────────────────────────
    ("openai/chatgpt-4o-latest", 373.0, 1120.0),
    ("openai/gpt-4-turbo", 747.0, 2240.0),
    ("openai/gpt-4.1", 299.0, 1194.0),
    ("openai/gpt-4.1-mini", 30.0, 119.0),
    ("openai/gpt-4.1-nano", 7.47, 30.0),
    ("openai/gpt-4o", 373.0, 1120.0),
    ("openai/gpt-4o-mini", 11.0, 45.0),
    ("openai/gpt-4o-mini-search-preview", 11.0, 45.0),
    ("openai/gpt-4o-search-preview", 373.0, 1120.0),
    ("openai/o1", 1120.0, 4480.0),
    ("openai/o1-mini", 224.0, 896.0),
    ("openai/o1-pro", 11200.0, 44800.0),
    ("openai/o3", 1494.0, 5976.0),
    ("openai/o3-mini", 299.0, 1194.0),
    ("openai/o3-pro", 14943.0, 59770.0),
    ("openai/o4-mini", 82.0, 327.0),
    ("openai/text-embedding-3-large", 9.33, 0.0),
    ("openai/text-embedding-3-small", 1.49, 0.0),

    # ── Perplexity ────────────────────────────────────────────────────────────
    ("perplexity/llama-3.1-sonar-large-128k-online", 60.0, 60.0),
    ("perplexity/llama-3.1-sonar-small-128k-online", 15.0, 15.0),
    ("perplexity/r1-1776", 52.0, 187.0),
    ("perplexity/sonar", 60.0, 60.0),
    ("perplexity/sonar-deep-research", 597.0, 597.0),
    ("perplexity/sonar-pro", 224.0, 897.0),
    ("perplexity/sonar-reasoning", 60.0, 299.0),
    ("perplexity/sonar-reasoning-pro", 224.0, 1494.0),

    # ── Qwen ──────────────────────────────────────────────────────────────────
    ("qwen/qwen-2.5-72b-instruct", 26.0, 26.0),
    ("qwen/qwen-2.5-7b-instruct", 4.48, 4.48),
    ("qwen/qwen-2.5-coder-32b-instruct", 22.0, 22.0),
    ("qwen/qwen-2.5-vl-3b-instruct", 4.48, 4.48),
    ("qwen/qwen-2.5-vl-7b-instruct", 4.48, 4.48),
    ("qwen/qwen-2.5-vl-72b-instruct", 26.0, 26.0),
    ("qwen/qwen-3-0.6b", 0.897, 0.897),
    ("qwen/qwen-3-1.7b", 1.49, 1.49),
    ("qwen/qwen-3-4b", 2.24, 2.24),
    ("qwen/qwen-3-8b", 4.48, 4.48),
    ("qwen/qwen-3-14b", 7.45, 7.45),
    ("qwen/qwen-3-30b-a3b", 7.45, 7.45),
    ("qwen/qwen-3-32b", 15.0, 15.0),
    ("qwen/qwen-3-235b-a22b", 26.0, 26.0),
    ("qwen/qwen-3-235b-a22b-free", 0.0, 0.0),
    ("qwen/qwq-32b", 22.0, 89.0),
    ("qwen/qwq-32b-preview", 22.0, 89.0),

    # ── xAI ───────────────────────────────────────────────────────────────────
    ("x-ai/grok-2-1212", 149.0, 447.0),
    ("x-ai/grok-3", 747.0, 2240.0),
    ("x-ai/grok-3-mini", 224.0, 448.0),
    ("x-ai/grok-3-mini-fast", 56.0, 112.0),
    ("x-ai/grok-4", 1494.0, 4480.0),
    ("x-ai/grok-4-mini", 112.0, 299.0),
    ("x-ai/grok-beta", 373.0, 1120.0),
]


async def seed():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    added = 0
    updated = 0
    async for db in get_session():
        for model, inp, out in PRICING:
            res = await db.execute(select(ModelPricing).where(ModelPricing.model == model))
            p = res.scalar_one_or_none()
            if p:
                p.input_price_per_1m = inp
                p.output_price_per_1m = out
                updated += 1
            else:
                db.add(ModelPricing(model=model, input_price_per_1m=inp, output_price_per_1m=out))
                added += 1
        await db.commit()
        print(f"Done: added {added}, updated {updated}")


if __name__ == "__main__":
    asyncio.run(seed())
