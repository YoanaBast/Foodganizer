from django import template

register = template.Library()


@register.filter
def title_except(value, exceptions="a,an,the,of,for,and,but"):
    words = value.split()
    exc = [w.lower() for w in exceptions.split(",")]
    result = [w.capitalize() if w.lower() not in exc else w.lower() for w in words]
    return " ".join(result)


@register.filter
def name_for_quantity_filter(unit, quantity):
    try:
        quantity = int(quantity)
    except ValueError:
        quantity = 1
    return unit.name_for_quantity(quantity)

@register.filter
def get_dict_item(dictionary, key):
    return dictionary.get(key, '')