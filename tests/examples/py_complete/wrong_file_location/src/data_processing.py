#!/usr/bin/env python3
"""
Data Processing Module
Advanced data manipulation and statistical functions
"""

import statistics
import json


def process_data(data: list, threshold: float = 0.5, normalize: bool = True) -> dict:
    """Process data with configurable threshold and normalization.

    Args:
        data (list): Input data to process
        threshold (float, optional): Processing threshold. Defaults to 0.5.
        normalize (bool, optional): Whether to normalize data. Defaults to True.

    Returns:
        list: Processed data
    """
    if not data:
        return []

    # Filter by threshold
    filtered = [item for item in data if item >= threshold]

    if normalize and filtered:
        max_val = max(filtered)
        min_val = min(filtered)
        if max_val != min_val:
            filtered = [(item - min_val) / (max_val - min_val) for item in filtered]

    return filtered


def filter_values(values, min_val=0, max_val=100, inclusive=True):
    """Filter values within a range.

    Args:
        values (list): List of values to filter
        min_val (int, optional): Minimum value. Defaults to 0.
        max_val (int, optional): Maximum value. Defaults to 100.
        inclusive (bool, optional): Whether to include boundary values. Defaults to True.

    Returns:
        list: Filtered values
    """
    if inclusive:
        return [v for v in values if min_val <= v <= max_val]
    else:
        return [v for v in values if min_val < v < max_val]


def calculate_statistics(data, precision=2, include_mode=False):
    """Calculate statistical measures for a dataset.

    Args:
        data (list): Input dataset
        precision (int, optional): Decimal precision. Defaults to 2.
        include_mode (bool, optional): Whether to include mode. Defaults to False.

    Returns:
        dict: Statistical measures
    """
    if not data:
        return {}

    # Ensure float output by explicitly converting to float before rounding
    result = {
        "mean": round(float(statistics.mean(data)), precision),
        "median": round(float(statistics.median(data)), precision),
        "std": round(statistics.stdev(data) if len(data) > 1 else 0.0, precision),
    }

    if include_mode:
        try:
            result["mode"] = statistics.mode(data)
        except statistics.StatisticsError:
            # When no unique mode exists, we'll omit the field rather than set None
            # This avoids type annotation issues and is cleaner
            pass

    return result


def transform_data(data, operation="double", factor=2, normalize=False, scale=1):
    """Transform data using specified operations.

    Args:
        data: Input data (dict, list, etc.)
        operation (str): Operation to perform
        factor (int): Multiplication factor
        normalize (bool): Whether to normalize
        scale (int): Scale factor

    Returns:
        Transformed data
    """
    if isinstance(data, dict):
        if operation == "multiply":
            return {k: v * factor for k, v in data.items()}
        else:  # default double
            return {k: v * 2 for k, v in data.items()}

    elif isinstance(data, list):
        if normalize:
            max_val = max(data) if data else 1
            return [x / max_val * scale for x in data]
        else:
            return [x * factor for x in data]

    return data
