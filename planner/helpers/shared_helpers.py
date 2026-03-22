from planner.models import UserMealList, UserGroceryList, UserFridge


def transfer_session_to_user(user, session):
    for item in session.pop('anon_fridge', []):
        UserFridge.objects.get_or_create(
            user=user,
            ingredient_id=item['ingredient_id'],
            unit_id=item['unit_id'],
            defaults={'quantity': item['quantity']}
        )

    for item in session.pop('anon_grocery', []):
        UserGroceryList.objects.get_or_create(
            user=user,
            ingredient_id=item['ingredient_id'],
            unit_id=item['unit_id'],
            defaults={'quantity': item['quantity']}
        )

    for item in session.pop('anon_meals', []):
        UserMealList.objects.create(
            user=user,
            recipe_id=item['recipe_id'],
        )

    anon_biometrics = session.pop('anon_biometrics', None)
    if anon_biometrics:
        from planner.models import UserBiometrics
        UserBiometrics.objects.get_or_create(
            user=user,
            defaults={
                'gender': anon_biometrics['gender'],
                'age': anon_biometrics['age'],
                'weight_kg': anon_biometrics['weight_kg'],
                'height_cm': anon_biometrics['height_cm'],
                'activity_level': anon_biometrics['activity_level'],
            }
        )
