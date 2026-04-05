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

from planner.helpers.calories_helpers import calculate_from_session, Tracker
from planner.helpers.calories_helpers import validate_calendar_quantity


class BiometricsView(View):
    template_name = 'planner/biometrics.html'

    def get(self, request):
        if request.user.is_authenticated:
            try:
                instance = request.user.biometrics
                form = BiometricsForm(instance=instance)
                biometrics = instance
            except UserBiometrics.DoesNotExist:
                form = BiometricsForm()
                biometrics = None
        else:
            anon_biometrics = request.session.get('anon_biometrics')
            if anon_biometrics:
                form = BiometricsForm(initial=anon_biometrics)
                biometrics = calculate_from_session(anon_biometrics)
            else:
                form = BiometricsForm()
                biometrics = None

        return render(request, self.template_name, {
            'form': form,
            'biometrics': biometrics,
        })

    def post(self, request):
        if request.user.is_authenticated:
            try:
                instance = request.user.biometrics
                form = BiometricsForm(request.POST, instance=instance)
            except UserBiometrics.DoesNotExist:
                form = BiometricsForm(request.POST)

            if form.is_valid():
                biometrics = form.save(commit=False)
                biometrics.user = request.user
                biometrics.save()
                return redirect('biometrics')

            return render(request, self.template_name, {
                'form': form,
                'biometrics': None,
            })

        else:
            form = BiometricsForm(request.POST)
            if form.is_valid():
                data = form.cleaned_data
                session_data = {
                    'gender': data['gender'],
                    'age': data['age'],
                    'weight_kg': data['weight_kg'],
                    'height_cm': data['height_cm'],
                    'activity_level': data['activity_level'],
                }
                request.session['anon_biometrics'] = session_data
                request.session.modified = True
                biometrics = calculate_from_session(session_data)
                return render(request, self.template_name, {
                    'form': form,
                    'biometrics': biometrics,
                })

            return render(request, self.template_name, {
                'form': form,
                'biometrics': None,
            })


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

        # get TDEE if biometrics exist
        tdee = None
        try:
            tdee = request.user.biometrics.tdee
        except Exception:
            pass

        # get all calendar entries for the month
        entries = CalendarEntry.objects.filter(
            user=request.user,
            date__year=year,
            date__month=month,
        ).select_related('recipe', 'ingredient', 'ingredient_unit')

        # build day data
        days = {}
        for entry in entries:
            key = str(entry.date)
            if key not in days:
                days[key] = {'kcal': 0, 'entries': []}
            days[key]['kcal'] = round(days[key]['kcal'] + entry.kcal, 2)
            days[key]['entries'].append({
                'id': entry.id,
                'source': entry.source,
                'name': entry.recipe.name if entry.recipe else entry.ingredient.name if entry.ingredient else '?',
                'kcal': entry.kcal,
                'servings': entry.servings,
                'quantity': entry.quantity,
                'unit': str(entry.ingredient_unit) if entry.ingredient_unit else None,
            })

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