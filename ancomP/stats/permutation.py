import numpy as np
import pandas as pd
from time import time
import copy
from scipy.stats import ttest_ind, f_oneway
import itertools

#from statsmodels.sandbox.stats.multicomp import multipletests

def _init_perms(vec, permutations=1000):
    """
    Creates a permutation matrix

    vec: numpy.array
       Array of values to be permuted
    permutations: int
       Number of permutations for permutation test

    Note: This can only handle binary classes now
    """
    c = len(vec)
    copy_vec = copy.deepcopy(vec)
    perms = np.array(np.zeros((c, permutations+1), dtype=vec.dtype))
    _samp_ones = np.array(np.ones(c), dtype=vec.dtype).transpose()
    for m in range(permutations+1):
        perms[:,m] = copy_vec
        np.random.shuffle(copy_vec)
    return perms

def _init_categorical_perms(cats, permutations=1000):
    """
    Creates a reciprocal permutation matrix

    cats: numpy.array
       List of binary class assignments
    permutations: int
       Number of permutations for permutation test

    Note: This can only handle binary classes now
    """
    c = len(cats)
    num_cats = len(np.unique(cats)) # Number of distinct categories
    copy_cats = copy.deepcopy(cats)
    perms = np.array(np.zeros((c, num_cats*(permutations+1)), dtype=cats.dtype))
    for m in range(permutations+1):
        for i in range(num_cats):
            perms[:,num_cats*m+i] = (copy_cats == i).astype(cats.dtype)
        np.random.shuffle(copy_cats)
    return perms


def _init_reciprocal_perms(cats, permutations=1000):
    """
    TODO: Make this function use _init_categorical_perms

    Creates a reciprocal permutation matrix

    cats: numpy.array
       List of binary class assignments
    permutations: int
       Number of permutations for permutation test

    Note: This can only handle binary classes now
    """
    num_cats = len(np.unique(cats)) #number of distinct categories
    c = len(cats)
    copy_cats = copy.deepcopy(cats)
    perms = np.array(np.zeros((c, num_cats*(permutations+1)), dtype=cats.dtype))
    _samp_ones = np.array(np.ones(c), dtype=cats.dtype).transpose()
    for m in range(permutations+1):
        #Perform division to make mean calculation easier
        perms[:,2*m] = copy_cats / float(copy_cats.sum())
        perms[:,2*m+1] = (_samp_ones - copy_cats) / float((_samp_ones - copy_cats).sum())
        np.random.shuffle(copy_cats)
    return perms


############################################################
## Mean permutation tests
############################################################

def _naive_mean_permutation_test(mat,cats,permutations=1000):
    """
    mat: numpy 2-d matrix
         columns: features (e.g. OTUs)
         rows: samples
         matrix of features
    cats: numpy array
         Array of categories to run group signficance on

    Note: only works on binary classes now

    Returns
    =======
    test_stats:
        List of mean test statistics
    pvalues:
        List of corrected p-values

    This module will conduct a mean permutation test using
    the naive approach
    """
    def _mean_test(values,cats):
        #calculates mean for binary categories
        return abs(values[cats==0].mean()-values[cats==1].mean())

    rows,cols = mat.shape
    pvalues = np.zeros(rows)
    test_stats = np.zeros(rows)
    for r in range(rows):
        values = mat[r,:].transpose()
        test_stat = _mean_test(values,cats)
        perm_stats = np.empty(permutations, dtype=np.float64)
        for i in range(permutations):
            perm_cats = np.random.permutation(cats)
            perm_stats[i] = _mean_test(values,perm_cats)
        p_value = ((perm_stats >= test_stat).sum() + 1.) / (permutations + 1.)
        pvalues[r] = p_value
        test_stats[r] = test_stat
    #_,pvalues,_,_ = multipletests(pvalues)
    return test_stats, pvalues

def _np_mean_permutation_test(mat, cats, permutations=1000):
    """
    mat: numpy.ndarray or scipy.sparse.*
         columns: features (e.g. OTUs)
         rows: samples
         matrix of features
    cats: numpy array
         Array of categories to run group signficance on
    permutations: int
         Number of permutations to calculate
    Note: only works on binary classes now

    Return
    ------
    test_stats:
        List of mean test statistics
    pvalues:
        List of corrected p-values

    This module will conduct a mean permutation test using
    numpy matrix algebra
    """
    perms = _init_reciprocal_perms(cats, permutations)
    _mat = np.matrix(mat)
    _perms = np.matrix(perms)
    return _np_two_sample_mean_statistic(_mat, _perms)

def _np_two_sample_mean_statistic(mat, perms):
    """
    Calculates a permutative mean statistic just looking at binary classes

    mat: numpy.ndarray or scipy.sparse.*
         columns: features (e.g. OTUs)
         rows: samples
         matrix of features
    perms: numpy.ndarray
         columns: permutations of samples
         rows: features
         Permutative matrix

    Note: only works on binary classes now

    Returns
    =======
    test_stats:
        List of mean test statistics
    pvalues:
        List of corrected p-values

    This module will conduct a mean permutation test using
    numpy matrix algebra
    """

    ## Create a permutation matrix
    num_cats = 2 #number of distinct categories
    n_otus, c = perms.shape
    permutations = (c-num_cats) // num_cats

    ## Perform matrix multiplication on data matrix
    ## and calculate averages
    avgs = mat * perms
    ## Calculate the mean statistic
    idx = np.arange(0, (permutations+1)*num_cats, num_cats)
    mean_stat = abs(avgs[:, idx+1] - avgs[:, idx])

    ## Calculate the p-values
    cmps =  mean_stat[:,1:] >= mean_stat[:,0]
    pvalues = (cmps.sum(axis=1)+1.)/(permutations+1.)

    #_,pvalues,_,_ = multipletests(pvalues)
    return map(np.array,[mean_stat[:,0],pvalues])



############################################################
## T-test permutation tests
############################################################
def _naive_t_permutation_test(mat,cats,permutations=1000):
    """
    mat: numpy 2-d matrix
         columns: features (e.g. OTUs)
         rows: samples
         matrix of features
    cats: numpy array
         Array of categories to run group signficance on

    Note: only works on binary classes now

    Returns
    =======
    test_stats:
        List of mean test statistics
    pvalues:
        List of corrected p-values

    This module will conduct a mean permutation test using
    the naive approach
    """
    def _t_test(values,cats):
        #calculates t statistic for binary categories
        T, _ =  ttest_ind(values[cats==0], values[cats==1], equal_var = False)
        return abs(T)

    rows,cols = mat.shape
    pvalues = np.zeros(rows)
    test_stats = np.zeros(rows)
    for r in range(rows):
        values = mat[r,:].transpose()
        test_stat = _t_test(values,cats)
        perm_stats = np.empty(permutations, dtype=np.float64)
        for i in range(permutations):
            perm_cats = np.random.permutation(cats)
            perm_stats[i] = _t_test(values,perm_cats)
        p_value = ((perm_stats >= test_stat).sum() + 1.) / (permutations + 1.)
        pvalues[r] = p_value
        test_stats[r] = test_stat
    #_,pvalues,_,_ = multipletests(pvalues)
    return test_stats, pvalues

def _np_t_permutation_test(mat, cats, permutations=1000):
    """
    mat: numpy.ndarray or scipy.sparse.*
         columns: features (e.g. OTUs)
         rows: samples
         matrix of features
    cats: numpy array
         Array of categories to run group signficance on
    permutations: int
         Number of permutations to calculate
    Note: only works on binary classes now

    Return
    ------
    test_stats:
        List of t-test statistics
    pvalues:
        List of corrected p-values

    This module will conduct a mean permutation test using
    numpy matrix algebra
    """
    perms = _init_categorical_perms(cats, permutations)
    _mat = np.matrix(mat)
    _perms = np.matrix(perms)
    return _np_two_sample_t_statistic(_mat, _perms)

def _np_two_sample_t_statistic(mat, perms):
    """
    Calculates a permutative Welch's t-statistic

    mat: numpy.matrix or scipy.sparse.*
         columns: features (e.g. OTUs)
         rows: samples
         matrix of features
    perms: numpy.matrix
         columns: permutations of samples
         rows: features
         Permutative matrix

    Note: only works on binary classes now

    Returns
    =======
    test_stats:
        List of t-test statistics
    pvalues:
        List of p-values

    This module will conduct a mean permutation test using
    numpy matrix algebra
    """
    assert type(mat) == np.matrix
    assert type(perms) == np.matrix

    ## Create a permutation matrix
    num_cats = 2 # number of distinct categories
    n_otus, c = perms.shape
    permutations = (c-num_cats) // num_cats

    ## Perform matrix multiplication on data matrix
    ## and calculate sums and squared sums
    _sums  = mat * perms
    _sums2 = np.multiply(mat,mat) * perms

    ## Calculate means and sample variances
    tot =  perms.sum(axis=0)
    _avgs  = _sums / tot
    _avgs2 = _sums2 / tot
    _vars  = _avgs2 - np.multiply(_avgs, _avgs)
    _samp_vars =  np.multiply(tot,_vars) / (tot-1)

    ## Calculate the t statistic
    idx = np.arange(0, (permutations+1)*num_cats, num_cats)
    denom  = np.sqrt(_samp_vars[:, idx+1] / tot[:,idx+1]  + _samp_vars[:, idx] / tot[:,idx])
    t_stat = np.divide(abs(_avgs[:, idx+1] - _avgs[:, idx]), denom)

    ## Calculate the p-values
    cmps =  t_stat[:,1:] >= t_stat[:,0]
    pvalues = (cmps.sum(axis=1)+1.)/(permutations+1.)

    return map(np.array, map(np.ravel, [t_stat[:,0],pvalues]))


############################################################
## F-test permutation tests
############################################################

"""
F = sum( MS_i for all i) /  MSE
"""
def _naive_f_permutation_test(mat,cats,permutations=1000):
    """
    Performs a 1-way ANOVA

    mat: numpy 2-d matrix
         columns: features (e.g. OTUs)
         rows: samples
         matrix of features
    cats: numpy array
         Array of categories to run group signficance on


    Returns
    =======
    test_stats:
        List of mean test statistics
    pvalues:
        List of corrected p-values

    This module will conduct a F permutation test using
    the naive approach
    """

    def _f_test(values,cats):
        #calculates t statistic for binary categories
        groups = []
        groups = [ values[cats==k] for k in set(cats) ]
        F, _ =  f_oneway(*groups)
        return abs(F)

    rows,cols = mat.shape
    pvalues = np.zeros(rows)
    test_stats = np.zeros(rows)
    for r in range(rows):
        values = mat[r,:].transpose()
        test_stat = _f_test(values,cats)
        perm_stats = np.empty(permutations, dtype=np.float64)
        for i in range(permutations):
            perm_cats = np.random.permutation(cats)
            perm_stats[i] = _f_test(values,perm_cats)
        p_value = ((perm_stats >= test_stat).sum() + 1.) / (permutations + 1.)
        pvalues[r] = p_value
        test_stats[r] = test_stat
    return test_stats, pvalues

def _np_k_sample_f_statistic(mat, cats, perms):
    """
    Calculates a permutative one way F test

    mat: numpy.array
         The contingency table.
         Columns correspond to features (e.g. OTUs)
         and rows correspond to  samples
    cat : numpy.array
         Vector of categories.
    perms: numpy.array
         Permutative matrix. Columns correspond to permutations
         of samples rows corespond to features

    Returns
    =======
    test_stats:
        List of f-test statistics
    pvalues:
        List of p-values

    This module will conduct a mean permutation test using
    numpy matrix algebra
    """

    ## Create a permutation matrix
    num_cats = len(np.unique(cats)) # Number of distinct categories
    n_samp, c = perms.shape
    permutations = (c-num_cats) / num_cats

    mat2 = np.multiply(mat, mat)

    S = mat.sum(axis=1)
    SS = mat2.sum(axis=1)
    sstot = SS - np.multiply(S,S) / float(n_samp)
    #Create index to sum the ssE together
    _sum_idx = _init_categorical_perms(
        np.arange((permutations+1)*num_cats,dtype=np.int32) // num_cats,
        permutations=0)


    ## Perform matrix multiplication on data matrix
    ## and calculate sums and squared sums and sum of squares
    _sums  = np.dot(mat, perms)
    _sums2 = np.dot(np.multiply(mat, mat), perms)
    tot =  perms.sum(axis=0)
    ss = _sums2 - np.multiply(_sums,_sums)/tot
    sserr = np.dot(ss, _sum_idx)
    sstrt = (sstot - sserr.T).T

    dftrt = num_cats-1
    dferr = np.dot(tot,_sum_idx) - num_cats
    f_stat = (sstrt / dftrt) / (sserr / dferr)
    cmps =  f_stat[:,1:].T >= f_stat[:,0]
    pvalues = (cmps.sum(axis=0)+1.) / (permutations+1.)
    return map(np.array, map(np.ravel, [f_stat[:, 0], pvalues]))

