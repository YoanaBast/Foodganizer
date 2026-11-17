from planner.services.biometrics_storage import get_biometrics
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.views import View
from django.shortcuts import render
from django.http import JsonResponse

import json
from datetime import date, datetime
from collections import defaultdict

from planner.models import CalendarEntry, UserBiometrics
from recipes.models import Recipe
from ingredients.models import Ingredient, MeasurementUnit, IngredientMeasurementUnit

from planner.forms import BiometricsForm
from planner.services.nutrition_tracker import EntryNutrients
from planner.services.nutrition_needs_core import coverage, needs_rows, nutrient_label
from core.constants import NUTRIENTS

from planner.helpers.calories_helpers import calculate_from_session, Tracker
from planner.helpers.calories_helpers import validate_calendar_quantity


class BiometricsView(View):
    template_name = 'planner/biometrics.html'

    def get(self, request):
        store = get_biometrics(request)
        summary = store.summary()
        needs = getattr(summary, 'nutrient_needs', None)  # only DB-backed biometrics have it
        return render(request, self.template_name, {
            'form': BiometricsForm(**store.form_kwargs()),
            'biometrics': summary,
            'needs_rows': needs_rows(needs) if needs else [],
        })

    def post(self, request):
        store = get_biometrics(request)
        form = BiometricsForm(request.POST, **store.form_kwargs())
        if form.is_valid():
            store.save(form)
            return redirect('biometrics')
        return render(request, self.template_name, {'form': form, 'biometrics': None})


class CalendarView(LoginRequiredMixin, View):
    template_name = 'planner/calendar.html'

    def get(self, request):
        return render(request, self.template_name)


class CalendarDataView(LoginRequiredMixin, View):
    """Returns JSON data for a given month"""

    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'not authenticated'}, status=403)

        year = int(request.GET.get('year', date.today().year))
        month = int(request.GET.get('month', date.today().month))

        # target calories and per-nutrient needs, if biometrics exist
        tdee = None
        needs = None
        try:
            biometrics = request.user.biometrics
            tdee = biometrics.target_calories
            needs = biometrics.nutrient_needs
        except Exception:
            pass

        entries = list(
            CalendarEntry.objects.filter(
                user=request.user,
                date__year=year,
                date__month=month,
            ).select_related(
                'recipe', 'ingredient', 'ingredient__default_unit', 'ingredient_unit'
            ).prefetch_related(
                'recipe__recipe_ingredient__ingredient',
                'recipe__recipe_ingredient__unit',
            )
        )

        # one calculator per request: caches per-serving recipe nutrients and
        # batch-loads ingredient/unit conversions
        calc = EntryNutrients(entries)

        days = {}
        for entry in entries:
            key = str(entry.date)
            day = days.setdefault(key, {'kcal': 0, 'nutrients': {}, 'entries': []})

            nutrients = calc.for_entry(entry)
            entry_kcal = nutrients['kcal']

            day['kcal'] = round(day['kcal'] + entry_kcal, 2)
            for n, v in nutrients.items():
                day['nutrients'][n] = round(day['nutrients'].get(n, 0) + v, 2)
            day['entries'].append({
                'id': entry.id,
                'source': entry.source,
                'name': entry.recipe.name if entry.recipe else entry.ingredient.name if entry.ingredient else '?',
                'kcal': entry_kcal,
                'servings': entry.servings,
                'quantity': entry.quantity,
                'unit': str(entry.ingredient_unit) if entry.ingredient_unit else None,
            })

        if needs:
            for day in days.values():
                day['coverage'] = [
                    dict(row, label=nutrient_label(row['nutrient']))
                    for row in coverage(day['nutrients'], needs)
                ]

        return JsonResponse({'days': days, 'tdee': tdee})



class CalendarAddEntryView(LoginRequiredMixin, View):
    def post(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'not authenticated'}, status=403)

        data = json.loads(request.body)
        entry_date = data.get('date')
        entry_type = data.get('type')

        if entry_type == 'recipe':
            servings, error = validate_calendar_quantity(data.get('servings'), 'Servings')
            if error:
                return JsonResponse({'error': error}, status=400)
            recipe = Recipe.objects.get(id=data['recipe_id'])
            CalendarEntry.objects.create(
                user=request.user,
                date=entry_date,
                recipe=recipe,
                servings=servings,
                source='manual_recipe',
            )

        elif entry_type == 'ingredient':
            quantity, error = validate_calendar_quantity(data.get('quantity'), 'Quantity')
            if error:
                return JsonResponse({'error': error}, status=400)
            ingredient = Ingredient.objects.get(id=data['ingredient_id'])
            unit = MeasurementUnit.objects.get(id=data['unit_id'])
            CalendarEntry.objects.create(
                user=request.user,
                date=entry_date,
                ingredient=ingredient,
                ingredient_unit=unit,
                quantity=quantity,
                source='manual_ingredient',
            )

        return JsonResponse({'ok': True})


class CalendarEditEntryView(LoginRequiredMixin, View):
    def post(self, request, entry_id):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'not authenticated'}, status=403)

        data = json.loads(request.body)
        entry = CalendarEntry.objects.get(id=entry_id, user=request.user)

        if entry.recipe:
            servings, error = validate_calendar_quantity(data.get('servings'), 'Servings')
            if error:
                return JsonResponse({'error': error}, status=400)
            entry.servings = servings
        elif entry.ingredient:
            quantity, error = validate_calendar_quantity(data.get('quantity'), 'Quantity')
            if error:
                return JsonResponse({'error': error}, status=400)
            entry.quantity = quantity
            if data.get('unit_id'):
                entry.ingredient_unit = MeasurementUnit.objects.get(id=data['unit_id'])

        entry.save()
        return JsonResponse({'ok': True})


class CalendarDeleteEntryView(LoginRequiredMixin, View):
    def post(self, request, entry_id):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'not authenticated'}, status=403)

        CalendarEntry.objects.filter(id=entry_id, user=request.user).delete()
        return JsonResponse({'ok': True})


class CalendarSearchView(LoginRequiredMixin, View):
    """Search recipes or ingredients for the add modal"""
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'not authenticated'}, status=403)

        q = request.GET.get('q', '')
        kind = request.GET.get('kind', 'recipe')

        if kind == 'recipe':
            results = Recipe.objects.filter(name__icontains=q)[:10]
            data = [{'id': r.id, 'name': r.name, 'kcal_per_serving': r.kcal_per_serving, 'servings': r.servings} for r in results]
        else:
            results = Ingredient.objects.filter(name__icontains=q)[:10]
            data = []
            for ing in results:
                units = list(ing.measurement_units.select_related('unit').values('unit__id', 'unit__name_singular'))
                data.append({'id': ing.id, 'name': ing.name, 'units': units})

        return JsonResponse({'results': data})


class CalendarDeficitView(LoginRequiredMixin, View):
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'not authenticated'}, status=403)

        start = request.GET.get('start')
        end = request.GET.get('end')

        if not start or not end:
            return JsonResponse({'error': 'missing dates'}, status=400)

        try:
            start_date = datetime.strptime(start, '%Y-%m-%d').date()
            end_date = datetime.strptime(end, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'invalid date format'}, status=400)

        if start_date > end_date:
            return JsonResponse({'error': 'start must be before end'}, status=400)

        # get TDEE
        try:
            tdee = request.user.biometrics.tdee
        except Exception:
            return JsonResponse({'error': 'no_biometrics'}, status=200)

        # build calories per day list
        entries = CalendarEntry.objects.filter(
            user=request.user,
            date__gte=start_date,
            date__lte=end_date,
        ).select_related('recipe', 'ingredient', 'ingredient_unit')

        # group by date
        day_kcal = defaultdict(float)
        for entry in entries:
            day_kcal[str(entry.date)] += entry.kcal

        # build list for every day in range (0 kcal for days with no entries)
        from datetime import timedelta
        fill_empty = request.GET.get('fill_empty', 'false').lower() == 'true'

        tdee_rounded = round(tdee, 2)

        current = start_date
        calories_per_days = []
        while current <= end_date:
            if str(current) in day_kcal:
                calories_per_days.append(round(day_kcal[str(current)], 2))
            else:
                calories_per_days.append(tdee_rounded if fill_empty else 0)
            current += timedelta(days=1)

        tracker = Tracker(
            maintenance_calories=tdee_rounded,  # ← same value as fill
            name=request.user.username
        )
        result = tracker.calculate_deficit(calories_per_days)

        return JsonResponse({
            'result': result,
            'days': len(calories_per_days),
            'total_consumed': round(sum(calories_per_days), 2),
            'total_maintenance': round(len(calories_per_days) * tdee, 2),
            'deficit': round(len(calories_per_days) * tdee - sum(calories_per_days), 2),
            'tdee': tdee,
        })

class CalendarNutrientRangeView(LoginRequiredMixin, View):
    """Nutrient totals vs. daily needs x days for a date range.

    Mirrors CalendarDeficitView: every day in the range counts, and fill_empty
    decides whether a day with no entries counts as meeting your needs (true)
    or as zero intake (false).
    """
    MAX_DAYS = 366

    def get(self, request):
        start = request.GET.get('start')
        end = request.GET.get('end')
        if not start or not end:
            return JsonResponse({'error': 'missing dates'}, status=400)

        try:
            start_date = datetime.strptime(start, '%Y-%m-%d').date()
            end_date = datetime.strptime(end, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({'error': 'invalid date format'}, status=400)

        if start_date > end_date:
            return JsonResponse({'error': 'start must be before end'}, status=400)

        days = (end_date - start_date).days + 1
        if days > self.MAX_DAYS:
            return JsonResponse({'error': f'range too long (max {self.MAX_DAYS} days)'}, status=400)

        try:
            needs = request.user.biometrics.nutrient_needs
        except Exception:
            return JsonResponse({'error': 'no_biometrics'}, status=200)

        fill_empty = request.GET.get('fill_empty', 'false').lower() == 'true'

        entries = list(
            CalendarEntry.objects.filter(
                user=request.user, date__gte=start_date, date__lte=end_date,
            ).select_related(
                'recipe', 'ingredient', 'ingredient__default_unit', 'ingredient_unit'
            ).prefetch_related(
                'recipe__recipe_ingredient__ingredient',
                'recipe__recipe_ingredient__unit',
            )
        )
        calc = EntryNutrients(entries)

        totals = defaultdict(float)
        logged = set()
        for entry in entries:
            for n, v in calc.for_entry(entry).items():
                totals[n] += v
            logged.add(entry.date)

        if fill_empty:
            empty_days = days - len(logged)
            for n in NUTRIENTS:
                totals[n] += needs.get(n, 0) * empty_days

        range_needs = {n: round(v * days, 2) for n, v in needs.items()}
        rows = [
            dict(
                row,
                label=nutrient_label(row['nutrient']),
                daily_need=needs[row['nutrient']],
                avg_per_day=round(row['intake'] / days, 2),
            )
            for row in coverage(totals, range_needs)
        ]

        return JsonResponse({
            'days': days,
            'logged_days': len(logged),
            'fill_empty': fill_empty,
            'rows': rows,
        })
