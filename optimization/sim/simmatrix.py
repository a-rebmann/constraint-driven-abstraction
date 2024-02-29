"""
Module which contains functionality for computing condensed similarity matrix

Notes
_____
Based on [1] https://github.com/scipy/scipy/blob/v1.4.1/scipy/spatial/distance.py#L1736-L2094
"""

import numpy as np
from math import sqrt


def compute_similarity_matrix(set_of_objects, sim_function, condensed=True):
    """
    Function calculates condensed similarity matrix basing on the pairwise
    distance between different models or nodes.

    Parameters
    ----------
    set_of_objects : list, tuple
        Set of nodes or models.
    sim_function : similarity function
        Function which takes two objects and returns the similarity.
    condensed : bool, optional
        If flag is True, matrix will be condensed.

    Returns
    -------
    condensed distance matrix : np.array
        For each i and j (where i < j < m), where m is the number of original observations.
        The metric of the matrix(set_of_objects[i], set_of_objects[j]) is computed and stored in entry ij.
    """
    set_length = len(set_of_objects)
    if condensed:
        matrix = np.empty((set_length * (set_length - 1)) // 2, dtype=np.double)

        counter = 0
        for i in range(set_length - 1):
            for j in range(i + 1, set_length):
                matrix[counter] = sim_function(set_of_objects[i], set_of_objects[j])
                counter += 1

        return matrix
    else:
        matrix = np.zeros((set_length, set_length), dtype=np.double)

        for i in range(set_length):
            for j in range(set_length):
                current = sim_function(set_of_objects[i], set_of_objects[j])
                matrix[i, j] = current

        return matrix


def compute_similarity_matrix_2sets(set_of_objects1, set_of_objects2, sim_function):
    """
    Function calculates condensed similarity matrix basing on the pairwise
    distance between different models or nodes.

    Parameters
    ----------
    set_of_objects1 : list, tuple
        Set of nodes or models.
    set_of_objects2 : list, tuple
        Set of nodes or models.
    sim_function : similarity function
        Function which takes two objects and returns the similarity.


    Returns
    -------
    condensed distance matrix : np.array
        The metric of the matrix(set_of_objects[i], set_of_objects[j]) is computed and stored in entry ij
        """
    set_length1 = len(set_of_objects1)
    set_length2 = len(set_of_objects2)

    matrix = np.empty((set_length1, set_length2), dtype=np.double)

    for i in range(set_length1):
        for j in range(set_length2):
            current = sim_function(set_of_objects1[i], set_of_objects2[j])
            matrix[i, j] = current

    return matrix


def convert_to_full_matrix(condensed_set_of_elements, similarity=False):
    """
    Method converts a condensed matrix into full one
    Initial matrix must be created from a one set of objects

    Parameters
    ----------
    similarity
    condensed_set_of_elements : list
        Condensed similarity matrix (one-dimensional).

    Returns
    -------
    full_matrix: np.array
        2-dimensional np.array, which represents a full version of the condensed matrix.
        All entries in the diagonal are equal 1, since they represent the same similarity value.
    """
    sum_of_elements = len(condensed_set_of_elements)

    if sum_of_elements < 2:
        return condensed_set_of_elements

    else:
        delta = int(1 + (8 * sum_of_elements))
        initial_elements_no = int(((-1 + sqrt(delta)) / 2) + 1)

        full_matrix = np.zeros((initial_elements_no, initial_elements_no), dtype=np.double)

        counter = 0
        k = initial_elements_no - 1
        for i in range(k):
            if similarity:
                full_matrix[i][i] = 0
            else:
                full_matrix[i][i] = 0
            for j in range(i + 1, k + 1):
                full_matrix[i][j] = condensed_set_of_elements[counter]
                full_matrix[j][i] = condensed_set_of_elements[counter]
                counter += 1
        if similarity:
            full_matrix[len(full_matrix)-1][len(full_matrix)-1] = 0
        return full_matrix


def convert_to_condensed_matrix(full_similarity_matrix):
    """
    Method converts a full matrix into condensed one.
    Initial matrix must be created from one set of objects.

    Parameters
    ----------
    full_similarity_matrix : np.array
        Two dimensional np.array that represents similarity matrix.

    Returns
    -------
    condensed distance matrix : np.array
        For each i and j (where i < j < m), where m is the number of original observations.
        The metric of the matrix(set_of_objects[i], set_of_objects[j]) is computed and stored in entry ij.
    """
    matrix_size = len(full_similarity_matrix)

    if matrix_size < 2:
        return full_similarity_matrix

    matrix = np.empty((matrix_size * (matrix_size - 1)) // 2, dtype=np.double)
    counter = 0
    for i in range(matrix_size - 1):
        for j in range(i + 1, matrix_size):
            matrix[counter] = full_similarity_matrix[i][j]
            counter += 1
    return matrix
