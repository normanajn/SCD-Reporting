"""Generate an AI-written narrative summary of a WorkItem queryset via the Anthropic API."""
import os

from django.conf import settings

from .exporters import _rows


def _format_entries(qs) -> str:
    parts = []
    for r in _rows(qs):
        flags = []
        if r['critical'] == 'yes':
            flags.append('CRITICAL')
        if r['highlight'] == 'yes':
            stars = '★' * int(r['highlight_stars']) if r['highlight_stars'] else ''
            flags.append(f'HIGHLIGHT {stars}'.strip())
        if r['private'] == 'yes':
            flags.append('PRIVATE')
        flag_str = f'  [{", ".join(flags)}]' if flags else ''
        group_str = f'  |  group: {r["group"]}' if r['group'] else ''
        tags_str = f'  |  tags: {r["tags"]}' if r['tags'] else ''
        desc_str = f'\n    {r["description"]}' if r['description'] else ''
        parts.append(
            f'- [{r["period_start"]} – {r["period_end"]}] {r["title"]}{flag_str}\n'
            f'  Author: {r["author"]}  |  {r["project"]} / {r["category"]}'
            + group_str
            + tags_str
            + desc_str
        )
    return '\n'.join(parts) if parts else '(no entries)'


def generate(qs) -> str:
    """Call the Anthropic API and return the summary as a Markdown string."""
    import anthropic
    from .models import AIPromptConfig

    api_key = getattr(settings, 'ANTHROPIC_API_KEY', '') or os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        raise ValueError(
            'ANTHROPIC_API_KEY is not configured. '
            'Set it as an environment variable or in Django settings.'
        )

    config = AIPromptConfig.get_solo()
    model = getattr(settings, 'ANTHROPIC_SUMMARY_MODEL', 'claude-sonnet-4-6')
    client = anthropic.Anthropic(api_key=api_key)
    message = client.messages.create(
        model=model,
        max_tokens=2048,
        system=config.system_prompt,
        messages=[{'role': 'user', 'content': config.user_template.format(entries=_format_entries(qs))}],
    )
    return message.content[0].text
