import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView
from django.db.models import Count

from core.utils import is_moderator
from ingredients.models import Ingredient, IngredientMeasurementUnit, IngredientDietaryTag
from .forms import RecipeForm, RecipeIngredientForm, RecipeIngredientFormSet
from .models import Recipe, RecipeCategory, RecipeIngredient


"""
RECIPE VIEWS
"""


class ManageRecipesView(ListView):
    model = Recipe
    template_name = 'recipes/manage_recipes.html'
    context_object_name = 'recipes'
    paginate_by = 10

    def get_queryset(self):
        search = self.request.GET.get('search', '')
        category = self.request.GET.get('category', '')
        tags = [t for t in self.request.GET.getlist('tag') if t]
        sort = self.request.GET.get('sort', '')

        qs = Recipe.objects.select_related('category').prefetch_related(
            'recipe_ingredient__ingredient__dietary_tag'
        ).annotate(fav_count=Count('favourited_by')).order_by('name')

        if search:
            qs = qs.filter(name__icontains=search)
        if category:
            qs = qs.filter(category__id=category)
        if tags:
            for tag_id in tags:
                qs = qs.exclude(
                    recipe_ingredient__in=RecipeIngredient.objects.exclude(
                        ingredient__dietary_tag__id=tag_id
                    )
                )
        if sort == 'kcal_asc':
            qs = sorted(qs, key=lambda r: r.kcal_per_serving)
        elif sort == 'kcal_desc':
            qs = sorted(qs, key=lambda r: r.kcal_per_serving, reverse=True)
        elif sort == 'popular':
            qs = qs.order_by('-fav_count')

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')
        context['categories'] = RecipeCategory.objects.all().order_by('name')
        context['tags'] = IngredientDietaryTag.objects.all().order_by('name')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_tags'] = [t for t in self.request.GET.getlist('tag') if t]
        context['selected_sort'] = self.request.GET.get('sort', '')
        for rec in context['recipes']:
            if self.request.user.is_authenticated:
                rec.is_fav = rec.favourited_by.filter(id=self.request.user.id).exists()
            else:
                rec.is_fav = False
        context['recipe_form'] = RecipeForm()
        context['ingredient_form'] = RecipeIngredientForm()
        return context


class RecipeDetailView(DetailView):
    model = Recipe
    template_name = 'recipes/recipe_detail.html'
    context_object_name = 'recipe'


class AddRecipeView(LoginRequiredMixin, View):
    template_name = 'recipes/add_recipe.html'

    def get_ingredients(self):
        return Ingredient.objects.prefetch_related('measurement_units__unit').all()

    def get(self, request):
        return render(request, self.template_name, {
            'recipe_form': RecipeForm(),
            'ingredient_formset': RecipeIngredientFormSet(),
            'ingredients': self.get_ingredients(),
        })

    def post(self, request):
        recipe_form = RecipeForm(request.POST)
        ingredient_formset = RecipeIngredientFormSet(request.POST)
        if recipe_form.is_valid() and ingredient_formset.is_valid():
            recipe = recipe_form.save(commit=False)
            recipe.created_by = request.user
            recipe.updated_by = request.user
            recipe.save()
            ingredient_formset.instance = recipe
            ingredient_formset.save()
            return redirect('recipe_detail', pk=recipe.pk)
        return render(request, self.template_name, {
            'recipe_form': recipe_form,
            'ingredient_formset': ingredient_formset,
            'ingredients': self.get_ingredients(),
        })


class DeleteRecipeView(LoginRequiredMixin, View):
    def post(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        if not is_moderator(request.user) and recipe.created_by != request.user:
            raise PermissionDenied
        recipe.delete()
        return redirect('manage_recipes')


class EditRecipeView(LoginRequiredMixin, View):
    template_name = 'recipes/edit_recipe.html'

    def get_forms(self, request, recipe):
        if request.method == 'POST':
            return (
                RecipeForm(request.POST, instance=recipe),
                RecipeIngredientFormSet(request.POST, instance=recipe)
            )
        return (
            RecipeForm(instance=recipe),
            RecipeIngredientFormSet(instance=recipe)
        )

    def get_context(self, recipe, recipe_form, ingredient_formset):
        existing_ids = [
            form.instance.ingredient_id
            for form in ingredient_formset.forms
            if form.instance.pk
        ]
        return {
            'recipe_form': recipe_form,
            'ingredient_formset': ingredient_formset,
            'ingredients': Ingredient.objects.prefetch_related('measurement_units__unit').exclude(id__in=existing_ids),
            'recipe': recipe,
            'default_url': reverse_lazy('manage_recipes'),
        }

    def get(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        if not is_moderator(request.user) and recipe.created_by != request.user:
            raise PermissionDenied
        recipe_form, ingredient_formset = self.get_forms(request, recipe)
        return render(request, self.template_name, self.get_context(recipe, recipe_form, ingredient_formset))

    def post(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        if not is_moderator(request.user) and recipe.created_by != request.user:
            raise PermissionDenied
        recipe_form, ingredient_formset = self.get_forms(request, recipe)
        if recipe_form.is_valid() and ingredient_formset.is_valid():
            recipe = recipe_form.save(commit=False)
            recipe.updated_by = request.user
            if not recipe.created_by:
                recipe.created_by = Recipe.objects.get(pk=pk).created_by
            recipe.save()
            ingredient_formset.save()
            return redirect('recipe_detail', pk=pk)
        return render(request, self.template_name, self.get_context(recipe, recipe_form, ingredient_formset))


"""
FAVOURITE HEART
"""

class ToggleFavouriteView(LoginRequiredMixin, View):
    def post(self, request, pk):
        recipe = get_object_or_404(Recipe, pk=pk)
        if recipe.favourited_by.filter(id=request.user.id).exists():
            recipe.favourited_by.remove(request.user)
            status = False
        else:
            recipe.favourited_by.add(request.user)
            status = True
        return JsonResponse({"favourited": status})

    def get(self, request, pk):
        return JsonResponse({'error': 'method not allowed'}, status=405)


"""
RECIPE INGREDIENT VIEWS
"""

class AddIngredientToRecipeView(View):
    def post(self, request, pk):
        try:
            data = json.loads(request.body)
            recipe = Recipe.objects.get(pk=pk)

            if not is_moderator(request.user) and recipe.created_by != request.user:
                return JsonResponse({"success": False, "error": "You do not have permission to edit this recipe."})

            ingredient_id = data.get("ingredient_id")
            quantity = data.get("quantity")
            unit_id = data.get("unit_id")

            try:
                quantity = float(quantity)
                if quantity <= 0:
                    return JsonResponse({"success": False, "error": "Quantity must be greater than 0."})
            except (ValueError, TypeError):
                return JsonResponse({"success": False, "error": "Please enter a valid quantity."})

            ingredient = Ingredient.objects.get(pk=ingredient_id)
            unit = IngredientMeasurementUnit.objects.get(pk=unit_id)

            ri, created = RecipeIngredient.objects.get_or_create(
                recipe=recipe,
                ingredient=ingredient,
                defaults={"quantity": quantity, "unit": unit}
            )
            if not created:
                ri.quantity = quantity
                ri.unit = unit
                ri.save()

            return JsonResponse({
                "success": True,
                "ingredient_name": ingredient.name,
                "quantity": quantity,
                "unit_name": unit.name_for_quantity(quantity),
                "ingredient_id": ingredient.id,
                "unit_id": unit.id,
            })
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})


"""
RECIPE CATEGORY VIEWS
"""

class AddRecipeCategoryAjaxView(View):
    def post(self, request):
        data = json.loads(request.body)
        name = data.get('name', '').strip().lower()
        if not name:
            return JsonResponse({'error': 'Name is required.'}, status=400)
        obj, created = RecipeCategory.objects.get_or_create(name=name)
        if not created:
            return JsonResponse({'error': f'"{name}" already exists.'}, status=400)
        if request.user.is_authenticated:
            obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
        return JsonResponse({'id': obj.id, 'name': obj.name})


class ListRecipeCategoriesAjaxView(View):
    def get(self, request):
        cats = RecipeCategory.objects.all().order_by('name')
        return JsonResponse({'items': [
            {
                'id': c.id,
                'name': c.name,
                'edit_url': reverse('edit_recipe_category_ajax', kwargs={'pk': c.id}),
                'delete_url': reverse('delete_recipe_category_ajax', kwargs={'pk': c.id}),
                'edit_fields': [
                    {'key': 'name', 'placeholder': 'Name', 'value': c.name},
                ]
            }
            for c in cats
        ]})


class EditRecipeCategoryAjaxView(View):
    def post(self, request, pk=None):
        if not pk:
            pk = request.POST.get("pk")
        name = request.POST.get("name", "").strip()
        if not name:
            return JsonResponse({"error": "Name required"}, status=400)
        cat = RecipeCategory.objects.filter(pk=pk).first()
        if not cat:
            return JsonResponse({"error": "Not found"}, status=404)
        if not is_moderator(request.user) and cat.created_by != request.user:
            return JsonResponse({"error": "You do not have permission to edit this."}, status=403)
        cat.name = name
        if request.user.is_authenticated:
            cat.updated_by = request.user
        cat.save()
        return JsonResponse({"id": cat.id, "name": cat.name})


class DeleteRecipeCategoryAjaxView(View):
    def post(self, request, pk=None):
        if not pk:
            pk = request.POST.get("pk")
        cat = RecipeCategory.objects.filter(pk=pk).first()
        if not cat:
            return JsonResponse({"error": "Not found"}, status=404)
        if not is_moderator(request.user) and cat.created_by != request.user:
            return JsonResponse({"error": "You do not have permission to edit this."}, status=403)
        cat.delete()
        return JsonResponse({"success": True})

