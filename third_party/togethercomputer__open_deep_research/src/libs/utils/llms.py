from typing import Any, Optional

import tenacity
from litellm import acompletion, completion
from together import Together


@tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=4, max=15))
async def asingle_shot_llm_call(
    model: str,
    system_prompt: str,
    message: str,
    response_format: Optional[dict[str, str | dict[str, Any]]] = None,
    max_completion_tokens: int | None = None,
) -> str:
    response = await acompletion(
        model=model,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": message}],
        temperature=0.0,
        response_format=response_format,
        # NOTE: max_token is deprecated per OpenAI API docs, use max_completion_tokens instead if possible
        # NOTE: max_completion_tokens is not currently supported by Together AI, so we use max_tokens instead
        max_tokens=max_completion_tokens,
        timeout=600,
    )
    return response.choices[0].message["content"]  # type: ignore


@tenacity.retry(stop=tenacity.stop_after_attempt(3), wait=tenacity.wait_exponential(multiplier=1, min=4, max=15))
def single_shot_llm_call(
    model: str,
    system_prompt: str,
    message: str,
    response_format: Optional[dict[str, str | dict[str, Any]]] = None,
    max_completion_tokens: int | None = None,
) -> str:
    response = completion(
        model=model,
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": message}],
        temperature=0.0,
        response_format=response_format,
        # NOTE: max_token is deprecated per OpenAI API docs, use max_completion_tokens instead if possible
        # NOTE: max_completion_tokens is not currently supported by Together AI, so we use max_tokens instead
        max_tokens=max_completion_tokens,
        timeout=600,
    )
    return response.choices[0].message["content"]  # type: ignore



def generate_toc_image(prompt: str, planning_model: str, topic: str) -> str:
    """Generate a table of contents image"""

    image_generation_prompt = single_shot_llm_call(
        model=planning_model, system_prompt=prompt, message=f"Research Topic: {topic}")

    if image_generation_prompt is None:
        raise ValueError("Image generation prompt is None")

    # HERE WE CALL THE TOGETHER API SINCE IT'S AN IMAGE GENERATION REQUEST
    client = Together()
    imageCompletion = client.images.generate(
        model="black-forest-labs/FLUX.1-dev",
        width=1024,
        height=768,
        steps=28,
        prompt=image_generation_prompt,
    )

    return imageCompletion.data[0].url  # type: ignore


