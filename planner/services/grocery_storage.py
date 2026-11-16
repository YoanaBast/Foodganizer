from planner.models import UserGroceryList
from planner.services.fridge_storage import DbStock, SessionStock


class GroceryMixin:
    def add_needed(self, final_needed):
        """final_needed: {ing_id: {'ingredient','unit','quantity',...}}"""
        for data in final_needed.values():
            unit = data['unit']
            self.add_by_ids(
                data['ingredient'].id, data['quantity'], unit.id if unit else None
            )

    def move_all_to(self, fridge):
        for e in self.all_entries():
            fridge.add_by_ids(e['ingredient_id'], e['quantity'], e['unit_id'])
        self.clear()

    def move_to(self, ref, fridge):
        for e in self.all_entries():
            if e['ref'] == ref:
                fridge.add_by_ids(e['ingredient_id'], e['quantity'], e['unit_id'])
                self.delete(ref)
                return True
        return False


class DbGrocery(GroceryMixin, DbStock):
    model = UserGroceryList


class SessionGrocery(GroceryMixin, SessionStock):
    key = 'anon_grocery'


def get_grocery(request):
    if request.user.is_authenticated:
        return DbGrocery(request.user)
    return SessionGrocery(request.session)
