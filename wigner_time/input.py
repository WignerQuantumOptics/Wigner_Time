# Copyright Thomas W. Clark & András Vukics 2024. Distributed under the Boost Software License, Version 1.0. (See accompanying file LICENSE.txt)

"""
A module for managing flexible input to entry-level timeline functions.
"""

import numpy as np

from wigner_time import util as WTutil


def __find_depth(vtvc):
    """
    Returns the necessary level of nesting to reach the data. This is complicated by the fact that the array input can be inhomogenously shaped (which is convenient for the user, if not for the programming!).
    """
    # TODO: Check that first element is actually a string.

    if WTutil.is_collection(vtvc[0]):
        if WTutil.is_collection(vtvc[0][0]):
            if WTutil.is_collection(vtvc[0][0][0]):
                raise ValueError("input involves too deeply nested array. ")
            else:
                return 3
        else:
            return 2
    else:
        return 1


def __ensure_time_context(collection, time, context=None, context__default=""):
    """
    Ensures the collection is in 2D, checks the dimensions of a single row of data and, where necessary, adds the `time` and `context` information to the data.
    """
    # TODO: Make more efficient

    shape_c = np.shape(collection)
    # print("shape_c: {}".format(shape_c))

    match len(shape_c):
        case 0:
            coll = [[collection]]
        case 1:
            coll = [collection]
        case 2:
            coll = collection
        case _:
            raise ValueError(
                "Problem with the structure of values in __ensure_time_context."
            )

    # print(f"coll[0] shape[-1]: {np.shape(coll[0])[-1]}")
    # print(f"coll: {coll}")
    # print(f"time: {time}")
    # print(f"context: {context}")
    match np.shape(coll[0])[-1]:
        case 3:
            return coll
        case 2:
            return [
                [row[0], row[1], context if context is not None else context__default]
                for row in coll
            ]

        case 1:
            if time is not None:
                if context:
                    return [[time, row[0], context] for row in coll]
                else:
                    return [
                        [time, row[0], row[1] if (len(row) > 1) else context__default]
                        for row in coll
                    ]
            else:
                raise ValueError(
                    "Badly formatted input to __ensure_time_context. Time is not specified."
                )
        case _:
            raise ValueError(
                "Badly formatted input to __ensure_time_context. Should have a final length of 1,2 or 3."
            )


def __correct_variable_list(coll2D, time, context):
    """
    Takes a 2D collection (array, list etc.) and runs the __ensure_time_context function appropriately.
    """
    return [[row[0], __ensure_time_context(row[1], time, context)] for row in coll2D]


def convert(
    *vtvc,
    time=None,
    context=None,
    **vtvc_dict,
):
    """
    INTERNAL function

    Defines the flexibility of input for basic timeline creation. Does this by converting various input strategies into a standardised form:
    [['variable', [
        [time001, value001],
        [time002,value002],
                  ...]]
    ['variable002', [...] ]]

    This was abstracted from `create`... to simplify (well, we tried) the logic.
    """
    # TODO: could probably still be simplified
    # TODO: make consistent: sometimes a tuple and sometimes a list

    shape = np.array(vtvc, dtype=object).shape

    if shape == (0,):
        return __correct_variable_list(vtvc_dict.items(), time, context)
    else:
        depth = __find_depth(vtvc)
        # print(f"depth: {depth}")
        #
        match depth:
            case 3:
                temp = __correct_variable_list(vtvc[0], time, context)
                # Assumed to be programmatic input
                # print('depth 3: ')
                return temp

            case 2:
                # print('depth 2: ')
                return __correct_variable_list(vtvc, time, context)
            case 1:
                # print("depth 1: ")
                vtvc = list(vtvc)

                vals = (
                    __ensure_time_context(vtvc[1], time, context)
                    if len(vtvc) == 2
                    else __ensure_time_context(vtvc[1:], time, context)
                )
                return [[vtvc[0], vals]]
            case _:
                return


def rows_from_input(input):
    """
    Takes input, where every variable has its own list, and converts the output to a list of length-4 lists.
    """
    # TODO: profiling suggests that this is very slow.
    # rows = []
    # for row in input:
    #     for rowv in row[1]:
    #         rows.append(np.concatenate([rowv[:1], [row[0]], rowv[1:]], dtype=object))
    # return rows

    rows = []
    a = rows.append

    for row in input:
        for rowv in row[1]:
            a(
                [
                    rowv[0],
                    row[0],
                    rowv[1],
                    rowv[2],
                ]
            )

    return rows


def rows_from_arguments(*vtvc, time=0.0, context=None, **vtvc_dict):
    # NOTE: What is the point of this function?
    return rows_from_input(convert(*vtvc, time=time, context=context, **vtvc_dict))


# =========================================================================
if __name__ == "__main__":
    convert(
        [
            ["AOM_imaging", [[0.0, 0.0]]],
            ["AOM_imaging__V", [[0.0, 2]]],
            ["AOM_repump", [[0.0, 1.0]]],
        ],
        context="init",
    )
