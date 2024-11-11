"""
Outlines the conventions for variables  and provides some convenience functions for working with them.
"""

separator_device = "_"
separator_unit = "__"


def info(
    variable: str, separator_device=separator_device, separator_unit=separator_unit
):
    """
    The convention is that a variable is represented by `thing_deviceOfManyParts__unit` for a non-digital unit and `thing_deviceOfManyParts` otherwise.
    """
    h_unit = variable.split(separator_unit)
    unit = h_unit[1] if len(h_unit) > 1 else "digital"
    thing_device = h_unit[0].split(separator_device)
    thing = thing_device[0]
    if len(thing_device[1:]) > 1:
        raise ValueError(
            f"Device specification in {variable} doesn't match the convention."
        )
    device = thing_device[1] if len(thing_device) > 1 else "digital"

    if device is None:
        raise ValueError(
            f"Variable {variable} doesn't meet the current naming convention."
        )
    if unit == "":
        raise ValueError(f"{variable} doesn't have an identifiable unit.")

    return {"thing": thing, "device": device, "unit": unit}


def unit(variable):
    return info(variable)["unit"]
