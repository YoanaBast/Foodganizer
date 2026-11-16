from planner.services.fridge_storage import SessionFridge
import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import ListView, UpdateView

from planner.forms import UserFridgeForm
from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from ingredients.models import Ingredient, MeasurementUnit
from planner.models import UserFridge

from django.views.generic import RedirectView

from planner.services.fridge_storage import get_fridge

class ManageFridgeView(RedirectView):
    pattern_name = 'generate_grocery_list'
    query_string = True

class ManageFridgeView_old(ListView):
    template_name = 'planner/fridge/manage_fridge.html'
    context_object_name = 'fridge'
    paginate_by = 10

    def get_queryset(self):
        if not self.request.user.is_authenticated:
            return UserFridge.objects.none()

        qs = UserFridge.objects.filter(user=self.request.user).select_related(
            'ingredient__category', 'ingredient__default_unit', 'unit'
        ).prefetch_related('ingredient__dietary_tag')

        search = self.request.GET.get('search', '')
        category = self.request.GET.get('category', '')
        tags = [t for t in self.request.GET.getlist('tag') if t]
        sort = self.request.GET.get('sort', '')

        if search:
            qs = qs.filter(ingredient__name__icontains=search)
        if category:
            qs = qs.filter(ingredient__category__id=category)
        if tags:
            for tag_id in tags:
                qs = qs.filter(ingredient__dietary_tag__id=tag_id)
            qs = qs.distinct()

        if sort == 'qty_asc':
            qs = qs.order_by('quantity')
        elif sort == 'qty_desc':
            qs = qs.order_by('-quantity')
        elif sort == 'kcal_asc':
            qs = qs.order_by('ingredient__base_quantity_kcal')
        elif sort == 'kcal_desc':
            qs = qs.order_by('-ingredient__base_quantity_kcal')
        else:
            qs = qs.order_by('ingredient__name')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ingredients'] = Ingredient.objects.all()
        context['search'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_tags'] = [t for t in self.request.GET.getlist('tag') if t]
        context['selected_sort'] = self.request.GET.get('sort', '')

        from ingredients.models import IngredientCategory, IngredientDietaryTag
        context['categories'] = IngredientCategory.objects.all().order_by('name')
        context['tags'] = IngredientDietaryTag.objects.all().order_by('name')

        if not self.request.user.is_authenticated:
            context['anon_fridge'] = get_fridge(self.request).resolved()
        return context


class AddFridgeItemView(View):
    def post(self, request):
        ing_id = request.POST.get("ingredient_id")
        ingredient = get_object_or_404(Ingredient, id=ing_id)

        form = UserFridgeForm(request.POST)
        if not form.is_valid():
            messages.error(request, list(form.errors.values())[0][0])
            return redirect('manage_fridge')

        qty = form.cleaned_data['quantity']
        unit = form.cleaned_data['unit']

        get_fridge(request).add(ingredient, qty, unit)

        return redirect('manage_fridge')


class EditFridgeItemView(LoginRequiredMixin, UpdateView):
    model = UserFridge
    form_class = UserFridgeForm
    template_name = 'planner/fridge/edit_fridge.html'
    pk_url_kwarg = 'item_id'
    success_url = reverse_lazy('manage_fridge')

    def get_queryset(self):
        # Scope lookups to the current user's own fridge items only —
        # without this, any authenticated user could load/edit any other
        # user's UserFridge row just by guessing item_id in the URL.
        return UserFridge.objects.filter(user=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['item'] = self.object
        context['ingredient_units'] = self.object.ingredient.measurement_units.select_related('unit').all()
        return context


class EditAnonFridgeItemView(View):

    def _entry(self, request, index):
        return next(
            (e for e in SessionFridge(request.session).all_entries() if e['ref'] == index),
            None,
        )

    def get(self, request, index):
        entry = self._entry(request, index)
        if not entry:
            return redirect('manage_fridge')
        ingredient = get_object_or_404(Ingredient, id=entry['ingredient_id'])
        return render(request, 'planner/fridge/edit_fridge.html', {
            'ingredient': ingredient,
            'quantity': entry['quantity'],
            'unit_id': entry['unit_id'],
            'ingredient_units': ingredient.measurement_units.select_related('unit').all(),
            'anon_index': index,
        })

    def post(self, request, index):
        if not self._entry(request, index):
            return JsonResponse({'error': 'Invalid index'}, status=400)

        store = SessionFridge(request.session)

        if request.headers.get('Content-Type') == 'application/json':
            try:
                data = json.loads(request.body)
                store.update(index, float(data.get('quantity')), int(data.get('unit_id')))
            except (json.JSONDecodeError, ValueError, TypeError):
                return JsonResponse({'error': 'Invalid quantity or unit.'}, status=400)
            return JsonResponse({'status': 'ok'})

        form = UserFridgeForm(request.POST)
        if form.is_valid():
            store.update(index, form.cleaned_data['quantity'], form.cleaned_data['unit'].id)
        return redirect('manage_fridge')


class DeleteFridgeItemView(View):
    def post(self, request, fridge_id):
        if request.user.is_authenticated:
            item = get_object_or_404(UserFridge, id=fridge_id, user=request.user)
            item.delete()
        return redirect('manage_fridge')

class EmptyFridgeView(View):
    def post(self, request):
        get_fridge(request).clear()
        return redirect('manage_fridge')

class DeleteAnonFridgeItemView(View):
    def post(self, request, index):
        SessionFridge(request.session).delete(index)
        return redirect('manage_fridge')
