"""Tests for AIPromptConfigForm user_template validation."""
import pytest

from apps.reports.forms import AIPromptConfigForm


def _form(template):
    return AIPromptConfigForm(data={
        'system_prompt': 'You are a helpful assistant.',
        'user_template': template,
    })


class TestUserTemplateValidation:
    def test_valid_template_accepted(self):
        assert _form('Summarize these entries:\n{entries}').is_valid()

    def test_escaped_braces_accepted(self):
        assert _form('Use {{literal braces}} and {entries}').is_valid()

    def test_unknown_placeholder_rejected(self):
        form = _form('Summarize {entries} and {missing}')
        assert not form.is_valid()
        assert 'missing' in form.errors['user_template'][0]

    def test_missing_entries_placeholder_rejected(self):
        form = _form('Summarize everything please.')
        assert not form.is_valid()
        assert '{entries}' in form.errors['user_template'][0]

    def test_malformed_syntax_rejected(self):
        form = _form('Bad {entries} syntax {unclosed')
        assert not form.is_valid()

    def test_only_entries_placeholder_accepted(self):
        assert _form('{entries}').is_valid()
