NUTRIENTS = [
    'kcal', 'protein', 'carbs', 'fat', 'fiber', 'sugar', 'salt', 'cholesterol',
    'vitamin_a', 'vitamin_c', 'vitamin_d', 'vitamin_e', 'vitamin_k',
    'vitamin_b1', 'vitamin_b2', 'vitamin_b3', 'vitamin_b6', 'vitamin_b12',
    'folate', 'calcium', 'iron', 'magnesium', 'potassium', 'zinc'
]
NUTRIENT_UNITS = {
    'kcal': 'kcal',
    'protein': 'g',
    'carbs': 'g',
    'fat': 'g',
    'fiber': 'g',
    'sugar': 'g',
    'salt': 'g',
    'cholesterol': 'g',
    'vitamin_a': 'µg',
    'vitamin_c': 'mg',
    'vitamin_d': 'µg',
    'vitamin_e': 'mg',
    'vitamin_k': 'µg',
    'vitamin_b1': 'mg',
    'vitamin_b2': 'mg',
    'vitamin_b3': 'mg',
    'vitamin_b6': 'mg',
    'vitamin_b12': 'µg',
    'folate': 'µg',
    'calcium': 'mg',
    'iron': 'mg',
    'magnesium': 'mg',
    'potassium': 'mg',
    'zinc': 'mg',
}

UNIT_SYSTEM_CHOICES = [
    ('metric', 'Metric (kg/cm)'),
    ('imperial', 'Imperial (lbs/inches)'),
]

DEFICIT_CHOICES = [
    ('maintain', 'No deficit (maintain)'),
    ('mild', 'Mild (-250 kcal)'),
    ('moderate', 'Moderate (-500 kcal)'),
    ('aggressive', 'Aggressive (-750 kcal)'),
]

DEFICIT_VALUES = {
    'maintain': 0,
    'mild': -250,
    'moderate': -500,
    'aggressive': -750,
}

GENDER_CHOICES = [
    ('M', 'Male'),
    ('F', 'Female'),
]

ACTIVITY_CHOICES = [
    ('sedentary', 'Sedentary (little or no exercise)'),
    ('light', 'Lightly Active (1-3 days/week)'),
    ('moderate', 'Moderately Active (3-5 days/week)'),
    ('very', 'Very Active (6-7 days/week)'),
    ('extra', 'Extra Active (physical job or 2x training)'),
]

ACTIVITY_MULTIPLIERS = {
    'sedentary': 1.2,
    'light': 1.375,
    'moderate': 1.55,
    'very': 1.725,
    'extra': 1.9,
}
