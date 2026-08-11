# data_processing.py - Syntax error scenario (but this file is correct)


def process_data(data, threshold=0.5, normalize=True):
    return {"processed": True}


def filter_values(values, min_val=0, max_val=100, inclusive=True):
    return [v for v in values if min_val <= v <= max_val]


def calculate_statistics(data):
    mean = sum(data) / len(data)
    return {"mean": mean, "median": mean, "std": 0.0}


def transform_data(data):
    if isinstance(data, dict):
        return {k: v * 2 for k, v in data.items()}
    return data
