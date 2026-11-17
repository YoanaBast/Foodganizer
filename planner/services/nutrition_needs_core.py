"""Pure nutrition-needs math. No DB, no session. Reference: US adult RDA/AI."""
from core.constants import NUTRIENTS, NUTRIENT_UNITS

LIMITS = {'sugar', 'salt', 'cholesterol'}  # upper limits, not targets


def bmi(weight_kg, height_cm):
    return round(weight_kg / (height_cm / 100) ** 2, 1)


def bmi_category(value):
    if value < 18.5:
        return 'Underweight'
    if value < 25:
        return 'Normal'
    if value < 30:
        return 'Overweight'
    return 'Obese'


def _pick(male, female, gender):
    return male if gender == 'M' else female


def daily_needs(gender, age, weight_kg, target_kcal):
    """{nutrient: amount per day} in NUTRIENT_UNITS. Limits are maximums."""
    older = age >= 51
    return {
        'kcal': round(target_kcal),
        'protein': round(0.8 * weight_kg, 1),
        'fat': round(target_kcal * 0.30 / 9, 1),
        'carbs': round(target_kcal * 0.50 / 4, 1),
        'fiber': round(target_kcal / 1000 * 14, 1),
        'sugar': round(target_kcal * 0.10 / 4, 1),
        'salt': 5.0,
        'cholesterol': 0.3,
        'vitamin_a': _pick(900, 700, gender),
        'vitamin_c': _pick(90, 75, gender),
        'vitamin_d': 20 if age >= 71 else 15,
        'vitamin_e': 15,
        'vitamin_k': _pick(120, 90, gender),
        'vitamin_b1': _pick(1.2, 1.1, gender),
        'vitamin_b2': _pick(1.3, 1.1, gender),
        'vitamin_b3': _pick(16, 14, gender),
        'vitamin_b6': _pick(1.7, 1.5, gender) if older else 1.3,
        'vitamin_b12': 2.4,
        'folate': 400,
        'calcium': 1200 if (gender == 'F' and older) or age >= 71 else 1000,
        'iron': 18 if gender == 'F' and not older else 8,
        'magnesium': _pick(420 if age >= 31 else 400, 320 if age >= 31 else 310, gender),
        'potassium': _pick(3400, 2600, gender),
        'zinc': _pick(11, 8, gender),
    }


def coverage(intake, needs):
    """
    intake: {nutrient: amount eaten}, needs: daily_needs() output.
    Returns [{'nutrient','unit','intake','need','percent','status','limit'}]
    status: 'deficient' (<50%), 'low' (<90%), 'ok', or 'over' (limits only).
    """
    rows = []
    for n in NUTRIENTS:
        if n == 'kcal' or n not in needs or not needs[n]:
            continue
        got = float(intake.get(n, 0) or 0)
        pct = round(got / needs[n] * 100)
        if n in LIMITS:
            status = 'over' if pct > 100 else 'ok'
        else:
            status = 'deficient' if pct < 50 else 'low' if pct < 90 else 'ok'
        rows.append({
            'nutrient': n, 'unit': NUTRIENT_UNITS.get(n, ''),
            'intake': round(got, 2), 'need': needs[n],
            'percent': pct, 'status': status, 'limit': n in LIMITS,
        })
    return rows


def nutrient_label(n):
    """'vitamin_b12' -> 'Vitamin B12', 'iron' -> 'Iron'."""
    if n.startswith('vitamin_'):
        return 'Vitamin ' + n[len('vitamin_'):].upper()
    return n.replace('_', ' ').capitalize()


def needs_rows(needs):
    """Display rows for the profile/biometrics page (kcal excluded, it has its own line)."""
    return [
        {'nutrient': n, 'label': nutrient_label(n), 'unit': NUTRIENT_UNITS.get(n, ''),
         'amount': needs[n], 'limit': n in LIMITS}
        for n in NUTRIENTS if n != 'kcal' and n in needs
    ]
