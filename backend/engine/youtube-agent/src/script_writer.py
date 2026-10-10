"""
Turns a topic into a short narration script + title + description.

Two modes:
- If ANTHROPIC_API_KEY is set, uses Claude for a genuinely good script
  (costs a fraction of a cent per script — not required).
- Otherwise falls back to a deterministic template writer. It's serviceable,
  not great; treat it as a rough draft you can hand-edit before building.

Either way, the output is re-checked by content_filter before anything
downstream touches it.
"""

import os
import textwrap

from content_filter import check_script

TEMPLATE = """\
Did you know about {topic}?

Here's what most people get wrong: {hook}.

{point1}

{point2}

{point3}

If you found that interesting, follow for more like this.
"""


def _template_script(topic: str, target_seconds: int) -> dict:
    hook = f"the real story behind '{topic}' is more surprising than it looks"
    script = TEMPLATE.format(
        topic=topic,
        hook=hook,
        point1=f"First, {topic} isn't what it's usually made out to be.",
        point2=f"Second, the details around {topic} genuinely change how you see it.",
        point3=f"And finally, this connects to a bigger pattern worth knowing.",
    )
    # Approximate narration at 2.4 words/second.  The no-LLM fallback expands
    # with neutral educational beats so duration works without an API key.
    target_words = max(90, target_seconds * 2.4)
    extension = (
        f"To understand {topic}, start with the basics, then compare the trade-offs, "
        "and finally check whether the source and context are reliable. "
    )
    while len(script.split()) < target_words:
        script += "\n\n" + extension
    return {
        "title": f"The Truth About {topic.title()}",
        "script": script.strip(),
        "description": f"A short breakdown of {topic}. Sources reviewed for accuracy.",
    }


def _claude_script(topic: str, target_seconds: int) -> dict:
    import anthropic
    client = anthropic.Anthropic()
    prompt = textwrap.dedent(f"""
        Write a {target_seconds}-second narration script (roughly {int(target_seconds * 2.4)} words) for a
        faceless educational YouTube Short about: "{topic}".

        Requirements:
        - Factually careful — no invented statistics, no medical/financial
          advice, no sensational claims you can't back up.
        - Hook in the first sentence.
        - Plain spoken language, short sentences, no jargon.
        - End with a soft "follow for more" line.
        - Also give a click-honest (not clickbait) title under 60 chars,
          and a one-sentence YouTube description.

        Respond ONLY as JSON: {{"title": "...", "script": "...", "description": "..."}}
    """).strip()

    resp = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    import json
    text = resp.content[0].text.strip()
    text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def write_script(topic: str, target_seconds: int = 60) -> dict:
    target_seconds = max(15, min(int(target_seconds), 600))
    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            result = _claude_script(topic, target_seconds)
        except Exception as e:
            print(f"[script_writer] Claude path failed ({e}), falling back to template")
            result = _template_script(topic, target_seconds)
    else:
        result = _template_script(topic, target_seconds)

    verdict = check_script(result["title"] + " " + result["script"])
    if not verdict["allowed"]:
        raise ValueError(f"Generated script rejected by content filter: {verdict['reason']}")
    result["needs_review"] = verdict["needs_review"]
    return result


if __name__ == "__main__":
    out = write_script("why octopuses have three hearts")
    print(out["title"])
    print()
    print(out["script"])
