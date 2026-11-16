from planner.models import UserMealList, UserGroceryList, UserFridge


def transfer_session_to_user(user, session):
    """Move everything an anonymous visitor built into their new account."""
    from planner.models import UserBiometrics
    from planner.services.fridge_storage import DbFridge, SessionFridge
    from planner.services.grocery_storage import DbGrocery, SessionGrocery

    for session_cls, db_cls in ((SessionFridge, DbFridge), (SessionGrocery, DbGrocery)):
        source, target = session_cls(session), db_cls(user)
        for e in source.all_entries():
            target.add_by_ids(e['ingredient_id'], e['quantity'], e['unit_id'])
        session.pop(session_cls.key, None)

    for item in session.pop('anon_meals', []):
        UserMealList.objects.create(user=user, recipe_id=item['recipe_id'])

    data = session.pop('anon_biometrics', None)
    if data:
        UserBiometrics.objects.get_or_create(user=user, defaults=data)
