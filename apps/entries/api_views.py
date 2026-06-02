import json
from datetime import date

from django.db import transaction
from django.db.models import F
from django.http import JsonResponse
from django.views import View

from apps.taxonomy.models import Category, LabPriority, Project, Tag, WorkGroup

from .models import WorkItem


def _json_error(message, status=400):
    return JsonResponse({'error': message}, status=status)


def _resolve_fk(model, value, allow_blank=False):
    """Resolve a slug or integer PK to a model instance. Returns (instance, error_str)."""
    if not value:
        if allow_blank:
            return None, None
        return None, f'{model.__name__} is required.'
    if str(value).isdigit():
        try:
            return model.objects.get(pk=int(value), is_active=True), None
        except model.DoesNotExist:
            pass
    try:
        return model.objects.get(slug=value, is_active=True), None
    except model.DoesNotExist:
        return None, f'{model.__name__} "{value}" not found or inactive.'


def _coerce_bool(val, default=False):
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ('true', '1', 'yes')
    return bool(val) if val is not None else default


def _coerce_int(val, default=0, lo=0, hi=5):
    try:
        return max(lo, min(hi, int(val)))
    except (TypeError, ValueError):
        return default


class EntryCreateAPIView(View):
    """POST /api/entries/ — create a work entry; returns JSON."""

    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required.'}, status=401)

        try:
            data = json.loads(request.body)
        except (ValueError, TypeError):
            return _json_error('Request body must be valid JSON.')

        if not isinstance(data, dict):
            return _json_error('Request body must be a JSON object.')

        errors = {}

        title = str(data.get('title', '')).strip()
        if not title:
            errors['title'] = 'This field is required.'

        description = str(data.get('description', '')).strip()
        if not description:
            errors['description'] = 'This field is required.'

        period_kind = data.get('period_kind', 'week')
        if period_kind not in WorkItem.PeriodKind.values:
            errors['period_kind'] = f'Must be one of: {", ".join(WorkItem.PeriodKind.values)}.'

        raw_start = data.get('period_start')
        raw_end = data.get('period_end')
        parsed_start = parsed_end = None

        if not raw_start:
            errors['period_start'] = 'This field is required.'
        else:
            try:
                parsed_start = date.fromisoformat(str(raw_start))
            except ValueError:
                errors['period_start'] = 'Date must be YYYY-MM-DD.'

        if not raw_end:
            errors['period_end'] = 'This field is required.'
        else:
            try:
                parsed_end = date.fromisoformat(str(raw_end))
            except ValueError:
                errors['period_end'] = 'Date must be YYYY-MM-DD.'

        if parsed_start and parsed_end and parsed_end < parsed_start:
            errors['period_end'] = 'period_end must be on or after period_start.'

        project, err = _resolve_fk(Project, data.get('project'))
        if err:
            errors['project'] = err

        category, err = _resolve_fk(Category, data.get('category'))
        if err:
            errors['category'] = err

        group, err = _resolve_fk(WorkGroup, data.get('group'), allow_blank=True)
        if err:
            errors['group'] = err

        lab_priority, err = _resolve_fk(LabPriority, data.get('lab_priority'), allow_blank=True)
        if err:
            errors['lab_priority'] = err

        if errors:
            return JsonResponse({'errors': errors}, status=400)

        with transaction.atomic():
            entry = WorkItem.objects.create(
                author=request.user,
                title=title,
                description=description,
                project=project,
                category=category,
                group=group,
                lab_priority=lab_priority,
                period_kind=period_kind,
                period_start=parsed_start,
                period_end=parsed_end,
                is_private=_coerce_bool(data.get('is_private')),
                is_critical=_coerce_bool(data.get('is_critical')),
                is_highlight=_coerce_bool(data.get('is_highlight')),
                highlight_stars=_coerce_int(data.get('highlight_stars')),
                is_division_head_only=_coerce_bool(data.get('is_division_head_only')),
            )

            tag_names = data.get('tags', [])
            if isinstance(tag_names, list):
                tags = []
                for name in tag_names:
                    name = str(name).strip().lower()
                    if name:
                        tag, created = Tag.objects.get_or_create(name=name)
                        Tag.objects.filter(pk=tag.pk).update(use_count=F('use_count') + 1)
                        tags.append(tag)
                if tags:
                    entry.tags.set(tags)

        from django.urls import reverse
        return JsonResponse({
            'id': entry.pk,
            'title': entry.title,
            'project': entry.project.slug,
            'category': entry.category.slug,
            'period_kind': entry.period_kind,
            'period_start': entry.period_start.isoformat(),
            'period_end': entry.period_end.isoformat(),
            'url': request.build_absolute_uri(reverse('entries:detail', kwargs={'pk': entry.pk})),
        }, status=201)
