from typing import List


class Tracker():
    KG_KCAL = 7830

    def __init__(self, maintenance_calories: int, name: str = "User"):
        self.maintenance_calories = maintenance_calories
        self.name = name

    def calculate_deficit(self, calories_per_days: List[float]) -> str:
        days = len(calories_per_days)
        total_maintenance_for_days = round(days * self.maintenance_calories, 2)
        total_consumed_for_days = round(sum(calories_per_days), 2)
        real_deficit = round(total_maintenance_for_days - total_consumed_for_days, 2)
        from_kg_fraction = round(real_deficit / self.KG_KCAL * 100, 1)

        if real_deficit > 0:
            return (
                f"{self.name}: Real deficit of {real_deficit} kcal. "
                f"That is {from_kg_fraction:.1f}% from 1kg of fat lost in {days} days."
            )

        if real_deficit < 0:
            return (
                f"{self.name}: Surplus of {abs(real_deficit)} kcal. "
                f"That is {abs(from_kg_fraction):.1f}% from 1kg of fat gained in {days} days."
            )

        return f"{self.name}: Perfect balance — no deficit or surplus over {days} days."


def track(name: str, maintenance_calories: int, calories_per_days: List[float]) -> str:
    tracker = Tracker(maintenance_calories, name)
    return tracker.calculate_deficit(calories_per_days)


def calculate_from_session(data):
    weight = data['weight_kg']
    height = data['height_cm']
    age = data['age']
    gender = data['gender']
    activity = data['activity_level']

    base = 10 * weight + 6.25 * height - 5 * age
    bmr = round(base + 5, 2) if gender == 'M' else round(base - 161, 2)

    multipliers = {
        'sedentary': 1.2,
        'light': 1.375,
        'moderate': 1.55,
        'very': 1.725,
        'extra': 1.9,
    }
    tdee = round(bmr * multipliers.get(activity, 1.2), 2)

    class AnonBiometrics:
        pass

    obj = AnonBiometrics()
    obj.bmr = bmr
    obj.tdee = tdee
    obj.updated_at = None
    return obj