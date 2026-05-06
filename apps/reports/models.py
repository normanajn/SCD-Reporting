from django.db import models

DEFAULT_SYSTEM = (
    "You are an analyst writing structured effort-reporting summaries for a scientific "
    "computing department. Your summaries are factual, professional, and well-organised. "
    "Use Markdown headings and bullet points. Do not invent information beyond what is provided."
)

DEFAULT_USER_TMPL = """\
Below is a set of effort entries from the SCD Reporting system.
Please write a concise narrative summary that includes:

1. **Overview** – date range covered, total entries, and authors involved.
2. **Key Themes** – the main types of work and projects represented.
3. **Notable Work** – standout contributions, especially any marked CRITICAL or HIGHLIGHT.
4. **Summary Table** – a compact Markdown table with columns: Author | Project | Category | Period | Title.

---
{entries}
"""


class AIPromptConfig(models.Model):
    system_prompt = models.TextField(default=DEFAULT_SYSTEM)
    user_template = models.TextField(default=DEFAULT_USER_TMPL)

    class Meta:
        verbose_name = 'AI Prompt Configuration'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'system_prompt': DEFAULT_SYSTEM,
                'user_template': DEFAULT_USER_TMPL,
            },
        )
        return obj
