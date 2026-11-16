"""Pure fridge math. No DB, no session. Works on plain dicts."""


def convert(qty, from_factor, to_factor):
    """Convert qty between two units via their conversion_to_base factors."""
    return float(qty) * float(from_factor) / float(to_factor)


def merge_stock(existing, qty, target_unit_id, factors):
    """
    existing: [{'unit_id', 'quantity'}] for ONE ingredient
    factors:  {unit_id: conversion_to_base} for that ingredient
    Folds every convertible entry into target_unit_id.
    Unconvertible entries are kept as separate rows.
    Returns the new entry list.
    """
    total = float(qty)
    kept = []
    for entry in existing:
        unit_id = entry['unit_id']
        if unit_id == target_unit_id:
            total += float(entry['quantity'])
        elif unit_id in factors and target_unit_id in factors:
            total += convert(entry['quantity'], factors[unit_id], factors[target_unit_id])
        else:
            kept.append({'unit_id': unit_id, 'quantity': float(entry['quantity'])})
    kept.append({'unit_id': target_unit_id, 'quantity': total})
    return kept


def available_in_unit(existing, target_unit_id, factors):
    """Total stock expressed in target_unit_id. Unconvertible entries are ignored."""
    total = 0.0
    for entry in existing:
        unit_id = entry['unit_id']
        if unit_id == target_unit_id:
            total += float(entry['quantity'])
        elif unit_id in factors and target_unit_id in factors:
            total += convert(entry['quantity'], factors[unit_id], factors[target_unit_id])
    return total


def shortfall(needed_qty, available_qty):
    """How much is still missing. 0 if the fridge covers it."""
    return round(max(float(needed_qty) - float(available_qty), 0.0), 4)


def subtract_stock(existing, qty, unit_id, factors):
    """
    Remove qty (in unit_id) from existing entries of ONE ingredient.
    Consumes across units via base quantity. Unconvertible entries stay.
    Returns the new entry list; empty entries are dropped.
    """
    if unit_id not in factors:
        return [dict(e) for e in existing]
    need_base = float(qty) * float(factors[unit_id])
    result = []
    for entry in existing:
        factor = factors.get(entry['unit_id'])
        if factor is None or need_base <= 0:
            result.append(dict(entry))
            continue
        entry_base = float(entry['quantity']) * float(factor)
        take = min(entry_base, need_base)
        need_base -= take
        remaining = round((entry_base - take) / float(factor), 4)
        if remaining > 0:
            result.append({'unit_id': entry['unit_id'], 'quantity': remaining})
    return result
