from django.conf import settings
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
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.CASCADE,
        related_name='ai_prompt_config',
    )
    system_prompt = models.TextField(default=DEFAULT_SYSTEM)
    user_template = models.TextField(default=DEFAULT_USER_TMPL)

    class Meta:
        verbose_name = 'AI Prompt Configuration'

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(
            pk=1,
            defaults={
                'user': None,
                'system_prompt': DEFAULT_SYSTEM,
                'user_template': DEFAULT_USER_TMPL,
            },
        )
        return obj

    @classmethod
    def for_user(cls, user):
        try:
            return user.ai_prompt_config
        except cls.DoesNotExist:
            return cls.get_solo()

    @classmethod
    def get_or_create_for_user(cls, user):
        global_config = cls.get_solo()
        obj, _ = cls.objects.get_or_create(
            user=user,
            defaults={
                'system_prompt': global_config.system_prompt,
                'user_template': global_config.user_template,
            },
        )
        return obj
