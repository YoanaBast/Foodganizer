from abc import abstractmethod

from django.db import transaction

from planner.models import UserGroceryList
from planner.services.fridge_storage import StockStorage

SESSION_KEY = 'anon_grocery'


class GroceryStorage(StockStorage):
    """Grocery list. Merge math is inherited; subclasses only persist."""

    @abstractmethod
    def all_entries(self):
        """[{'ingredient_id', 'unit_id', 'quantity'}] for the whole list."""

    def add_needed(self, final_needed):
        """final_needed: output of fridge.missing() / build_needed_dict shape."""
        for data in final_needed.values():
            unit = data['unit']
            self.add_by_ids(
                data['ingredient'].id, data['quantity'], unit.id if unit else None
            )

    def move_all_to(self, fridge):
        for e in self.all_entries():
            fridge.add_by_ids(e['ingredient_id'], e['quantity'], e['unit_id'])
        self.clear()


class DbGrocery(GroceryStorage):
    def __init__(self, user):
        self.user = user

    def _qs(self, ingredient_id=None):
        qs = UserGroceryList.objects.filter(user=self.user)
        return qs.filter(ingredient_id=ingredient_id) if ingredient_id else qs

    def entries(self, ingredient_id):
        return [{'unit_id': r.unit_id, 'quantity': r.quantity} for r in self._qs(ingredient_id)]

    @transaction.atomic
    def replace(self, ingredient_id, entries):
        self._qs(ingredient_id).delete()
        UserGroceryList.objects.bulk_create([
            UserGroceryList(user=self.user, ingredient_id=ingredient_id,
                            unit_id=e['unit_id'], quantity=e['quantity'])
            for e in entries
        ])

    def all_entries(self):
        return [
            {'ingredient_id': r.ingredient_id, 'unit_id': r.unit_id, 'quantity': r.quantity}
            for r in self._qs()
        ]

    def clear(self):
        self._qs().delete()


class SessionGrocery(GroceryStorage):
    def __init__(self, session):
        self.session = session

    def _items(self):
        return self.session.get(SESSION_KEY, [])

    def entries(self, ingredient_id):
        return [
            {'unit_id': i['unit_id'], 'quantity': i['quantity']}
            for i in self._items() if i['ingredient_id'] == ingredient_id
        ]

    def replace(self, ingredient_id, entries):
        others = [i for i in self._items() if i['ingredient_id'] != ingredient_id]
        others += [{'ingredient_id': ingredient_id, **e} for e in entries]
        self.session[SESSION_KEY] = others
        self.session.modified = True

    def all_entries(self):
        return [dict(i) for i in self._items()]

    def clear(self):
        self.session[SESSION_KEY] = []
        self.session.modified = True


def get_grocery(request):
    if request.user.is_authenticated:
        return DbGrocery(request.user)
    return SessionGrocery(request.session)
