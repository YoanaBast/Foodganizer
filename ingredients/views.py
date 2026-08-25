import json
import math

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView

from core.constants import NUTRIENT_UNITS
from core.mixins import OwnerOrModeratorMixin
from core.utils import is_moderator
from .models import Ingredient, IngredientMeasurementUnit, IngredientCategory, IngredientDietaryTag, MeasurementUnit
from .forms import IngredientAddForm, IngredientEditForm, IngredientDetailForm


"""
INGREDIENT VIEWS
"""

class ManageIngredientsView(ListView):
    model = Ingredient
    template_name = 'ingredients/manage_ingredients.html'
    context_object_name = 'ingredients'
    paginate_by = 10

    def get_queryset(self):
        qs = Ingredient.objects.select_related(
            'category', 'default_unit'
        ).prefetch_related('dietary_tag').order_by('name')
        search = self.request.GET.get('search', '')
        category = self.request.GET.get('category', '')
        tags = [t for t in self.request.GET.getlist('tag') if t]
        sort = self.request.GET.get('sort', '')
        if search:
            qs = qs.filter(name__icontains=search)
        if category:
            qs = qs.filter(category__id=category)
        if tags:
            for tag_id in tags:
                qs = qs.filter(dietary_tag__id=tag_id)
            qs = qs.distinct()
        if sort == 'kcal_asc':
            qs = qs.order_by('base_quantity_kcal')
        elif sort == 'kcal_desc':
            qs = qs.order_by('-base_quantity_kcal')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = IngredientCategory.objects.all().order_by('name')
        context['tags'] = IngredientDietaryTag.objects.all().order_by('name')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_tags'] = [t for t in self.request.GET.getlist('tag') if t]
        context['selected_sort'] = self.request.GET.get('sort', '')
        context['search'] = self.request.GET.get('search', '')
        return context


class AddIngredientView(LoginRequiredMixin, CreateView):
    model = Ingredient
    form_class = IngredientAddForm
    template_name = 'ingredients/add_ingredient.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['nutrient_units'] = NUTRIENT_UNITS
        return context


    def form_valid(self, form):
        ingredient = form.save(commit=False)
        ingredient.name = ingredient.name.strip().lower()
        ingredient.created_by = self.request.user
        ingredient.updated_by = self.request.user
        ingredient.save()
        form.save_m2m()
        if ingredient.default_unit:
            IngredientMeasurementUnit.objects.get_or_create(
                ingredient=ingredient,
                unit=ingredient.default_unit,
                defaults={'conversion_to_base': 1}
            )
        return redirect('edit_ingredient', ingredient_id=ingredient.id)

    def form_invalid(self, form):
        return render(self.request, self.template_name, {'form': form})


class EditIngredientView(LoginRequiredMixin, OwnerOrModeratorMixin, UpdateView):
    model = Ingredient
    form_class = IngredientEditForm
    template_name = 'ingredients/edit_ingredient.html'
    pk_url_kwarg = 'ingredient_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['ingredient'] = self.object
        context['nutrients'] = Ingredient.NUTRIENTS
        context['nutrient_units'] = NUTRIENT_UNITS
        context['default_url'] = reverse_lazy('manage_ingredients')
        context['all_units'] = MeasurementUnit.objects.all().order_by('name_singular')

        # ensure default unit always exists in measurement_units
        if self.object.pk and self.object.default_unit:
            IngredientMeasurementUnit.objects.get_or_create(
                ingredient=self.object,
                unit=self.object.default_unit,
                defaults={'conversion_to_base': 1}
            )
        return context

    def form_valid(self, form):
        ingredient = form.save(commit=False)
        ingredient.name = ingredient.name.strip().lower()
        ingredient.updated_by = self.request.user
        ingredient.save()
        form.save_m2m()
        return redirect('edit_ingredient', ingredient_id=ingredient.id)

    def form_invalid(self, form):
        return render(self.request, self.template_name, self.get_context_data(form=form))


class DeleteIngredientView(LoginRequiredMixin, OwnerOrModeratorMixin, View):
    def post(self, request, ingredient_id):
        ing = get_object_or_404(Ingredient, pk=ingredient_id)
        is_mod = request.user.groups.filter(name='Moderator').exists()
        is_owner = ing.created_by == request.user
        if not is_mod and not is_owner:
            raise PermissionDenied
        ing.delete()
        return redirect('manage_ingredients')


class IngredientDetailView(View):
    def get(self, request, ingredient_id):
        return self._render(request, ingredient_id)

    def post(self, request, ingredient_id):
        return self._render(request, ingredient_id)

    def _render(self, request, ingredient_id):
        ingredient = get_object_or_404(Ingredient, pk=ingredient_id)
        form = IngredientDetailForm(ingredient, request.POST or None)
        quantity = form.get_quantity()
        unit = form.get_unit()
        quantity = int(quantity) if quantity == int(quantity) else quantity
        nutrients = form.get_nutrients()

        nutrient_items = list(nutrients.items())
        col_size = math.ceil(len(nutrient_items) / 3)
        nutrient_columns = [
            nutrient_items[i:i + col_size]
            for i in range(0, len(nutrient_items), col_size)
        ]

        return render(request, 'ingredients/ingredient_detail.html', {
            'ingredient': ingredient,
            'form': form,
            'unit_name': unit.name_for_quantity(quantity),
            'nutrients': nutrients,
            'nutrient_columns': nutrient_columns,
            'quantity': quantity,
            'created_by': ingredient.created_by,
            'updated_by': ingredient.updated_by,
            'selected_imu': unit,
        })

"""
INGREDIENT CATEGORY VIEWS
"""

class ListCategoriesAjaxView(View):
    def get(self, request):
        cats = IngredientCategory.objects.all().order_by('name')
        return JsonResponse({'items': [
            {
                'id': c.id,
                'name': c.name,
                'edit_url': reverse('edit_category_ajax', kwargs={'pk': c.id}),
                'delete_url': reverse('delete_category_ajax', kwargs={'pk': c.id}),
                'edit_fields': [
                    {'key': 'name', 'placeholder': 'Name', 'value': c.name},
                ]
            }
            for c in cats
        ]})


class AddCategoryAjaxView(View):
    def post(self, request):
        data = json.loads(request.body)
        name = data.get('name', '').strip().lower()
        if not name:
            return JsonResponse({'error': 'Name is required.'}, status=400)
        obj, created = IngredientCategory.objects.get_or_create(name=name)
        if not created:
            return JsonResponse({'error': f'"{name}" already exists.'}, status=400)
        if request.user.is_authenticated:
            obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
        return JsonResponse({'id': obj.id, 'name': obj.name})


class EditCategoryAjaxView(View):
    def post(self, request, pk):
        cat = IngredientCategory.objects.filter(pk=pk).first()
        if not cat:
            return JsonResponse({"error": "Not found"}, status=404)
        if not is_moderator(request.user) and cat.created_by != request.user:
            return JsonResponse({"error": "You do not have permission to edit this."}, status=403)
        name = request.POST.get("name")
        if not name:
            return JsonResponse({"error": "Name required"}, status=400)
        cat.name = name
        if request.user.is_authenticated:
            cat.updated_by = request.user
        cat.save()
        return JsonResponse({"id": cat.id, "name": cat.name})


class DeleteCategoryAjaxView(View):
    def post(self, request, pk):
        cat = IngredientCategory.objects.filter(pk=pk).first()
        if not cat:
            return JsonResponse({"error": "Not found"}, status=404)
        if not is_moderator(request.user) and cat.created_by != request.user:
            return JsonResponse({"error": "You do not have permission to delete this."}, status=403)
        cat.delete()
        return JsonResponse({"success": True})


"""
INGREDIENT DIETARY TAGS VIEWS
"""

class DietaryTagsFragmentView(View):
    def get(self, request):
        form = IngredientAddForm()
        return HttpResponse(str(form['dietary_tag']))


class ListDietaryTagsAjaxView(View):
    def get(self, request):
        tags = IngredientDietaryTag.objects.all().order_by('name')
        return JsonResponse({'items': [
            {
                'id': t.id,
                'name': t.name,
                'edit_url': reverse('edit_dietary_tag_ajax', kwargs={'pk': t.id}),
                'delete_url': reverse('delete_dietary_tag_ajax', kwargs={'pk': t.id}),
                'edit_fields': [
                    {'key': 'name', 'placeholder': 'Name', 'value': t.name},
                ]
            }
            for t in tags
        ]})


class AddDietaryTagAjaxView(View):
    def post(self, request):
        data = json.loads(request.body)
        name = data.get('name', '').strip().lower()
        if not name:
            return JsonResponse({'error': 'Name is required.'}, status=400)
        obj, created = IngredientDietaryTag.objects.get_or_create(name=name)
        if not created:
            return JsonResponse({'error': f'"{name}" already exists.'}, status=400)
        if request.user.is_authenticated:
            obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
        return JsonResponse({'id': obj.id, 'name': obj.name})


class EditDietaryTagAjaxView(View):
    def post(self, request, pk):
        tag = IngredientDietaryTag.objects.filter(pk=pk).first()
        if not tag:
            return JsonResponse({"error": "Not found"}, status=404)
        if not is_moderator(request.user) and tag.created_by != request.user:
            return JsonResponse({"error": "You do not have permission to edit this."}, status=403)
        name = request.POST.get("name")
        if not name:
            return JsonResponse({"error": "Name required"}, status=400)
        tag.name = name
        if request.user.is_authenticated:
            tag.updated_by = request.user
        tag.save()
        return JsonResponse({"id": tag.id, "name": tag.name})


class DeleteDietaryTagAjaxView(View):
    def post(self, request, pk):
        tag = IngredientDietaryTag.objects.filter(pk=pk).first()
        if not tag:
            return JsonResponse({"error": "Not found"}, status=404)
        if not is_moderator(request.user) and tag.created_by != request.user:
            return JsonResponse({"error": "You do not have permission to delete this."}, status=403)
        tag.delete()
        return JsonResponse({"success": True})


"""
INGREDIENT MEASUREMENT UNITS VIEWS
"""

class AddMeasurementUnitView(View):
    def post(self, request, ingredient_id):
        ingredient = get_object_or_404(Ingredient, pk=ingredient_id)
        equals_base_unit_id = request.POST.get('unit')
        secondary_quantity = request.POST.get('conversion_to_base')

        # 1pc base, user said it equals 120 grams (secondary)
        # 1g = ? pc? 1/120 = 0.008
        # base_quantity / secondary_quantity = 1 / 120
        # conversion = 0.008

        # 100 grams base, user said it equals 10 tbsp (secondary)
        # 1tbsp = ? gram? 10
        # base_quantity / secondary_quantity = 100 / 10
        # conversion = 10


        print("DEBUG")
        if not secondary_quantity:
            messages.error(request, 'Conversion to base is required.')
            return redirect(reverse('edit_ingredient', kwargs={'ingredient_id': ingredient_id}))

        try:
            conversion_float = float(ingredient.base_quantity) / float(secondary_quantity)
            print(f"DEBUG conversion_float{conversion_float}, ingredient.base_quantity{ingredient.base_quantity}. secondary_quantity{secondary_quantity}")

        except (ValueError, TypeError, ZeroDivisionError):
            messages.error(request, 'Please enter a valid number for conversion.')

            return redirect(reverse('edit_ingredient', kwargs={'ingredient_id': ingredient_id}))

        if conversion_float <= 0:
            messages.error(request, 'Conversion to base must be greater than 0.')
            return redirect(reverse('edit_ingredient', kwargs={'ingredient_id': ingredient_id}))
        elif conversion_float > 100_000:
            messages.error(request, 'Conversion to base must be less than 100 000.')
            return redirect(reverse('edit_ingredient', kwargs={'ingredient_id': ingredient_id}))

        if equals_base_unit_id:
            unit = get_object_or_404(MeasurementUnit, pk=equals_base_unit_id)
            obj, created = IngredientMeasurementUnit.objects.get_or_create(
                ingredient=ingredient,
                unit=unit,
                defaults={'conversion_to_base': conversion_float}
            )
            if not created:
                messages.error(request, f'"{unit.name_singular}" is already added for this ingredient.')
            else:
                messages.success(request, f'"{unit.name_singular}" added successfully.')

        return redirect(reverse('edit_ingredient', kwargs={'ingredient_id': ingredient_id}))


class AddMeasurementUnitAjaxView(View):
    def post(self, request):
        data = json.loads(request.body)
        code = data.get('code', '').strip().lower()
        name_singular = data.get('name_singular', '').strip().lower()
        name_plural = data.get('name_plural', '').strip().lower()
        if not all([code, name_singular, name_plural]):
            return JsonResponse({'error': 'All fields are required.'}, status=400)
        obj, created = MeasurementUnit.objects.get_or_create(
            code=code,
            defaults={'name_singular': name_singular, 'name_plural': name_plural}
        )
        if not created:
            return JsonResponse({'error': f'Unit with code "{code}" already exists.'}, status=400)
        if request.user.is_authenticated:
            obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
        return JsonResponse({'id': obj.id, 'name': f'{obj.name_singular} ({obj.code})'})


class DeleteMeasurementUnitView(View):
    def post(self, request, ingredient_id, imu_id):
        imu = get_object_or_404(IngredientMeasurementUnit, pk=imu_id)
        imu.delete()
        return redirect('edit_ingredient', ingredient_id=ingredient_id)


class ListMeasurementUnitsAjaxView(View):
    def get(self, request):
        units = MeasurementUnit.objects.all().order_by('name_singular')
        return JsonResponse({'items': [
            {
                'id': u.id,
                'name': f'{u.name_singular} ({u.code})',
                'edit_url': reverse('edit_measurement_unit_ajax', kwargs={'pk': u.id}),
                'delete_url': reverse('delete_measurement_unit_ajax', kwargs={'pk': u.id}),
                'edit_fields': [
                    {'key': 'name_singular', 'placeholder': 'Singular (e.g. gram)', 'value': u.name_singular},
                    {'key': 'name_plural', 'placeholder': 'Plural (e.g. grams)', 'value': u.name_plural},
                    {'key': 'code', 'placeholder': 'Code (e.g. g)', 'value': u.code},
                ]
            }
            for u in units
        ]})


class EditMeasurementUnitAjaxView(View):
    def post(self, request, pk):
        unit = get_object_or_404(MeasurementUnit, pk=pk)
        name_singular = request.POST.get('name_singular', '').strip()
        name_plural = request.POST.get('name_plural', '').strip()
        if not name_singular:
            return JsonResponse({'error': 'Name is required.'}, status=400)
        if not is_moderator(request.user) and unit.created_by != request.user:
            return JsonResponse({"error": "You do not have permission to edit this."}, status=403)
        unit.name_singular = name_singular
        if name_plural:
            unit.name_plural = name_plural
        if request.user.is_authenticated:
            unit.updated_by = request.user
        unit.save()
        return JsonResponse({'id': unit.id, 'name': f'{unit.name_singular} ({unit.code})'})


class DeleteMeasurementUnitAjaxView(View):
    def post(self, request, pk):
        unit = get_object_or_404(MeasurementUnit, pk=pk)
        if not is_moderator(request.user) and unit.created_by != request.user:
            return JsonResponse({"error": "You do not have permission to delete this."}, status=403)
        unit.delete()
        return JsonResponse({'success': True})


class EditMeasurementUnitConversionView(View):
    def post(self, request, ingredient_id, imu_id):
        imu = get_object_or_404(IngredientMeasurementUnit, pk=imu_id)
        conversion = request.POST.get('conversion_to_base')
        try:
            conversion_float = float(conversion)
            if conversion_float <= 0:
                messages.error(request, 'Conversion must be greater than 0.')
            elif conversion_float > 100_000:
                messages.error(request, 'Conversion must be less than 100 000.')
            else:
                imu.conversion_to_base = conversion_float
                imu.save()

                imu.ingredient.updated_by = request.user
                imu.ingredient.save()

                messages.success(request, 'Conversion updated.')
        except (ValueError, TypeError):
            messages.error(request, 'Please enter a valid number.')
        return redirect(reverse('edit_ingredient', kwargs={'ingredient_id': ingredient_id}))


"""
Old function-based views below:
"""

# def edit_ingredient(request, ingredient_id):
#     default_url = reverse('manage_ingredients')
#     ing = get_object_or_404(Ingredient, pk=ingredient_id)
#
#     if request.method == "POST":
#         form = IngredientEditForm(request.POST, instance=ing)
#         if form.is_valid():
#             ingredient = form.save(commit=False)
#             ingredient.name = ingredient.name.strip().lower()
#             try:
#                 ingredient.save()
#                 form.save_m2m()
#
#                 # Ensure IngredientMeasurementUnit exists for default unit
#                 if ingredient.default_unit:
#                     IngredientMeasurementUnit.objects.get_or_create(
#                         ingredient=ingredient,
#                         unit=ingredient.default_unit,
#                         defaults={'conversion_to_base': 1}
#                     )
#
#             except IntegrityError:
#                 messages.error(request, f'"{ingredient.name}" already exists.')
#                 return render(request, "ingredients/edit_ingredient.html", {
#                     "form": form,
#                     "ingredient": ing,
#                     "nutrients": Ingredient.NUTRIENTS,
#                     'default_url': default_url,
#                     'all_units': MeasurementUnit.objects.all().order_by('name_singular'),
#                 })
#             return redirect('edit_ingredient', ingredient_id=ingredient.id)
#
#     else:
#         form = IngredientEditForm(instance=ing)
#
#     context = {
#         "form": form,
#         "ingredient": ing,
#         "nutrients": Ingredient.NUTRIENTS,
#         'default_url': default_url,
#         'all_units': MeasurementUnit.objects.all().order_by('name_singular'),
#     }
#     return render(request, "ingredients/edit_ingredient.html", context)


# def manage_ingredients(request):
#     ingredients_qs = Ingredient.objects.select_related(
#         'category', 'default_unit'
#     ).prefetch_related(
#         'dietary_tag'
#     ).all().order_by('name')
#
#     paginator = Paginator(ingredients_qs, 10)
#     page_number = request.GET.get('page')
#     ingredients = paginator.get_page(page_number)
#
#     add_form = IngredientAddForm()
#
#     context = {
#         'ingredients': ingredients,
#         'add_form': add_form,
#         'nutrients': Ingredient.NUTRIENTS,
#         'add_url': reverse('add_ingredient'),
#     }
#
#     return render(request, 'ingredients/manage_ingredients.html', context)


# def add_ingredient(request):
#     form = IngredientAddForm(request.POST or None)
#
#     if request.method == 'POST':
#         if form.is_valid():
#             ingredient = form.save(commit=False)
#             ingredient.name = ingredient.name.strip().lower()
#             try:
#                 ingredient.save()
#                 form.save_m2m()
#
#                 if ingredient.default_unit:
#                     IngredientMeasurementUnit.objects.get_or_create(
#                         ingredient=ingredient,
#                         unit=ingredient.default_unit,
#                         defaults={'conversion_to_base': 1}
#                     ) -> redundant - handled in forms.py
#
#                 return redirect('edit_ingredient', ingredient_id=ingredient.id)
#             except IntegrityError:
#                 messages.error(request, f'"{ingredient.name}" already exists.')
#
#     return render(request, 'ingredients/add_ingredient.html', {'form': form})

# def delete_ingredient(request, ingredient_id):
#     ing = get_object_or_404(Ingredient, pk=ingredient_id)
#     if request.method == 'POST':
#         ing.delete()
#         return redirect('manage_ingredients')
#     return render(request, 'ingredients/ingredient_delete_confirm.html', {'ingredient': ing})