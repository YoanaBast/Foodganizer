import json

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import ListView, DetailView

from core.utils import is_moderator
from ingredients.models import Ingredient, IngredientMeasurementUnit
from .forms import RecipeForm, RecipeIngredientForm, RecipeIngredientFormSet
from .models import Recipe, RecipeCategory, RecipeIngredient

# Create your views here.


"""
RECIPE VIEWS
"""

class ManageRecipesView(ListView):
    """
    A dashboard of all recipes
    """
    model = Recipe
    template_name = 'recipes/manage_recipes.html'
    context_object_name = 'recipes'
    paginate_by = 10

    def get_queryset(self):
        search = self.request.GET.get('search', '')
        qs = Recipe.objects.all().order_by('name')
        if search:
            qs = qs.filter(name__icontains=search)
        return qs


    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search'] = self.request.GET.get('search', '')

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
    """
    HTML delete button (trash bin) -> JS pop-up -> openDeleteModal (delete_popup.js)
    -> Delete button in the pop-up posts to URL (/recipes/pk/delete/) -> URL calls DeleteRecipeView
    """
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
Note:
Because OwnerOrModeratorMixin works by overriding get_object() which is a method on Django's SingleObjectMixin — it's designed for CBVs that use get_object() like UpdateView, DetailView, DeleteView.
EditRecipeView and DeleteRecipeView are plain View subclasses that manually call get_object_or_404 — so get_object() is never called and the mixin does nothing.

Note:
AJAX views will be kept as FBV as they just return a JSON response. CBV would add nothing to them. 
"""


"""
FAVOURITE HEART
"""


@login_required
def toggle_favourite(request, pk):
    if request.method != 'POST':
        return JsonResponse({'error': 'method not allowed'}, status=405)

    recipe = get_object_or_404(Recipe, pk=pk)

    if recipe.favourited_by.filter(id=request.user.id).exists():
        recipe.favourited_by.remove(request.user)
        status = False
    else:
        recipe.favourited_by.add(request.user)
        status = True

    return JsonResponse({"favourited": status})


"""
RECIPE INGREDIENT VIEWS
"""

def add_ingredient(request, pk):
    if request.method == "POST":
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

def add_recipe_category_ajax(request):
    if request.method == 'POST':
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
    return JsonResponse({'error': 'Invalid method.'}, status=405)


def list_categories_ajax(request):
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


def edit_category_ajax(request, pk=None):
    if request.method == "POST":
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

    return JsonResponse({"error": "Invalid method"}, status=405)



def delete_category_ajax(request, pk=None):
    if request.method == "POST":
        if not pk:
            pk = request.POST.get("pk")

        cat = RecipeCategory.objects.filter(pk=pk).first()

        if not cat:
            return JsonResponse({"error": "Not found"}, status=404)

        if not is_moderator(request.user) and cat.created_by != request.user:
            return JsonResponse({"error": "You do not have permission to edit this."}, status=403)

        cat.delete()
        return JsonResponse({"success": True})
    return JsonResponse({"error": "Invalid method"}, status=405)


"""
Older views:
"""

# def manage_recipes(request):
#     user, _ = User.objects.get_or_create(username="default")
#     recipes_qs = Recipe.objects.all().order_by('name')
#     paginator = Paginator(recipes_qs, 10)
#     page_number = request.GET.get('page')
#     recipes = paginator.get_page(page_number)
#
#     for rec in recipes:
#         rec.is_fav = rec.favourited_by.filter(id=user.id).exists()
#
#     recipe_form = RecipeForm()
#     ingredient_form = RecipeIngredientForm()
#
#     context = {
#         'recipes': recipes,
#         'recipe_form': recipe_form,
#         'ingredient_form': ingredient_form,
#     }
#     return render(request, 'recipes/manage_recipes.html', context)


# def recipe_detail(request, pk):
#     recipe = get_object_or_404(Recipe, pk=pk)
#     return render(request, 'recipes/recipe_detail.html', {'recipe': recipe})


# def add_recipe(request):
#     ingredients = Ingredient.objects.prefetch_related('measurement_units__unit').all()
#
#     if request.method == 'POST':
#         recipe_form = RecipeForm(request.POST)
#         ingredient_formset = RecipeIngredientFormSet(request.POST)
#
#         if recipe_form.is_valid() and ingredient_formset.is_valid():
#             try:
#                 recipe = recipe_form.save(commit=False)
#
#                 recipe.name = recipe.name.strip().lower()
#                 recipe.save()
#             except IntegrityError:
#                 messages.error(request, f'"{recipe.name}" already exists.')
#                 return render(request, 'recipes/add_recipe.html', {
#                     'recipe_form': recipe_form,
#                     'ingredient_formset': ingredient_formset,
#                     'ingredients': ingredients,
#                 })
#
#             ingredient_formset.instance = recipe
#             ingredient_formset.save()
#             return redirect('recipe_detail', pk=recipe.pk)
#         else:
#             # Catch duplicate caught at form validation level
#             name_errors = recipe_form.errors.get('name', [])
#             if any('already exists' in e for e in name_errors):
#                 name = request.POST.get('name', '').strip().lower()
#                 messages.error(request, f'"{name}" already exists.')
#     else:
#         recipe_form = RecipeForm()
#         ingredient_formset = RecipeIngredientFormSet()
#
#     return render(request, 'recipes/add_recipe.html', {
#         'recipe_form': recipe_form,
#         'ingredient_formset': ingredient_formset,
#         'ingredients': ingredients,
#     })


# def delete_recipe(request, pk):
#     recipe = get_object_or_404(Recipe, pk=pk)
#     recipe.delete()
#     return redirect('manage_recipes')


# def edit_recipe(request, pk):
#     default_url = reverse('manage_recipes')
#     recipe = get_object_or_404(Recipe, pk=pk)
#
#     if request.method == 'POST':
#         recipe_form = RecipeForm(request.POST, instance=recipe)
#         ingredient_formset = RecipeIngredientFormSet(request.POST, instance=recipe)
#
#         if recipe_form.is_valid() and ingredient_formset.is_valid():
#             try:
#                 updated_recipe = recipe_form.save(commit=False)
#                 updated_recipe.name = updated_recipe.name.strip().lower()
#                 updated_recipe.save()
#                 ingredient_formset.save()
#                 return redirect('recipe_detail', pk=recipe.pk)
#             except IntegrityError:
#                 messages.error(request, f'"{updated_recipe.name}" already exists.')
#         else:
#             name_errors = recipe_form.errors.get('name', [])
#             if any('already exists' in e for e in name_errors):
#                 name = request.POST.get('name', '').strip().lower()
#                 messages.error(request, f'"{name}" already exists.')
#     else:
#         recipe_form = RecipeForm(instance=recipe)
#         ingredient_formset = RecipeIngredientFormSet(instance=recipe)
#
#     existing_ids = [form.instance.ingredient_id for form in ingredient_formset.forms if form.instance.pk]
#     ingredients_add = Ingredient.objects.prefetch_related('measurement_units__unit').exclude(id__in=existing_ids)
#
#     context = {
#         'recipe_form': recipe_form,
#         'ingredient_formset': ingredient_formset,
#         'ingredients': ingredients_add,
#         'recipe': recipe,
#         'default_url': default_url,
#     }
#     return render(request, 'recipes/edit_recipe.html', context)
