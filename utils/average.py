def calculate_average(grades):
    """Calculate the average of a list of grades."""
    if not grades:
        return 0.0
    return round(sum(grades) / len(grades), 2)
