"""
Commonly used functions and utilities
"""

from textwrap import dedent
from functools import wraps

from six import iteritems
from numpy import array, ndarray, fabs, where

from serpentTools.messages import (
    error,
    critical,
    identical,
    notIdentical,
    acceptableLow,
    acceptableHigh,
    outsideTols,
    differentTypes,
    logMissingKeys,
    logBadTypes,
    logBadShapes,
    )

LOWER_LIM_DIVISION = 1E-8
"""Lower limit for denominator for division"""


def str2vec(iterable, of=float, out=array):
    """
    Convert a string or other iterable to vector.

    Parameters
    ----------
    iterable: str or iterable
        If string, will be split with ``split(splitAt)``
        to create a list. Every item in this list, or original
        iterable, will be iterated over and converted accoring
        to the other arguments.
    of: type
        Convert each value in ``iterable`` to this data type.
    out: type
        Return data type. Will be passed the iterable of
        converted items of data dtype ``of``.

    Returns
    -------
    vector
        Iterable of all values of ``iterable``, or split variant,
        converted to type ``of``.

    Examples
    --------
    ::

        >>> v = "1 2 3 4"
        >>> str2vec(v)
        array([1., 2., 3., 4.,])

        >>> str2vec(v, int, list)
        [1, 2, 3, 4]

        >>> x = [1, 2, 3, 4]
        >>> str2vec(x)
        array([1., 2., 3., 4.,])

    """
    vec = (iterable.split() if isinstance(iterable, str)
           else iterable)
    return out([of(xx) for xx in vec])


def splitValsUncs(iterable, copy=False):
    """
    Return even and odd indexed values from iterable

    Designed to extract expected values and uncertainties from
    SERPENT vectors of the form
    ``[x1, u1, x2, u2, ...]``

    Parameters
    ----------
    iterable: ndarray or iterable
        Initial arguments to be processed. If not
        :py:class:`numpy.ndarray`, then will be converted
        by calling :py:func:`serpentTools.utils.str2vec`
    copy: bool
        If true, return a unique instance of the values
        and uncertainties. Otherwise, returns a view
        per numpy slicing methods

    Returns
    -------
    numpy.ndarray
        Even indexed values from ``iterable``
    numpy.ndarray
        Odd indexed values from ``iterable``

    Examples
    --------
    ::

        >>> v = [1, 2, 3, 4]
        >>> splitValsUncs(v)
        array([1, 3]), array([2, 4])

        >>> line = "1 2 3 4"
        >>> splitValsUnc(line)
        array([1, 3]), array([2, 4])

    """

    if not isinstance(iterable, ndarray):
        iterable = str2vec(iterable)
    vals = iterable[0::2]
    uncs = iterable[1::2]
    if copy:
        return vals.copy(), uncs.copy()
    return vals, uncs


def convertVariableName(variable):
    """
    Return the mixedCase version of a SERPENT variable.

    Parameters
    ----------
    variable: str
        ``SERPENT_STYLE`` variable name to be converted

    Returns
    -------
    str:
        Variable name that has been split at underscores and
        converted to ``mixedCase``

    Examples
    --------
    ::

        >>> v = "INF_KINF"
        >>> convertVariableName(v)
        infKinf

        >>> v = "VERSION"
        >>> convertVariableName(v)
        version

    """
    lowerSplits = [item.lower() for item in variable.split('_')]
    if len(lowerSplits) == 1:
        return lowerSplits[0]
    return lowerSplits[0] + ''.join([item.capitalize()
                                     for item in lowerSplits[1:]])


LEADER_TO_WIKI = "http://serpent.vtt.fi/mediawiki/index.php/"


def linkToWiki(subLink, text=None):
    """
    Return a string that will render as a hyperlink to the SERPENT wiki.

    Parameters
    ----------
    subLink: str
        Desired path inside the SERPENT wiki - following the
        ``index.php``
    text: None or str
        If given, use this as the shown text for the full link.

    Returns
    -------
    str:
        String that can be used as an rst hyperlink to the
        SERPENT wiki

    Examples
    --------
    >>> linkToWiki('Input_syntax_manual')
    http://serpent.vtt.fi/mediawiki/index.php/Input_syntax_manual
    >>> linkToWiki('Description_of_output_files#Burnup_calculation_output',
    ...            "Depletion Output")
    `Depletion Output <http://serpent.vtt.fi/mediawiki/index.php/
    Description_of_output_files#Burnup_calculation_output>`_
    """
    fullLink = LEADER_TO_WIKI + subLink
    if not text:
        return fullLink
    return "`{} <{}>`_".format(text, fullLink)


COMPARE_DOC_DESC = """
    desc0: dict or None
    desc1: dict or None
        Description of the origin of each value set. Only needed
        if ``quiet`` evalues to ``True."""
COMPARE_DOC_HERALD = """herald: callable
        Function that accepts a single string argument used to
        notify that differences were found. If
        the function is not a callable object, a
        :func:`serpentTools.messages.critical` message
        will be printed and :func:`serpentTools.messages.error`
        will be used."""
COMPARE_DOC_LIMITS = """
    lower: float or int
        Lower limit for relative tolerances in percent
        Differences below this will be considered allowable
    upper: float or int
        Upper limit for relative tolerances in percent. Differences
        above this will be considered failure and errors
        messages will be raised"""
COMPARE_DOC_SIGMA = """sigma: int
        Size of confidence interval to apply to
        quantities with uncertainties. Quantities that do not
        have overlapping confidence intervals will fail"""
COMPARE_DOC_TYPE_ERR = """TypeError
        If ``other`` is not of the same class as this class
        nor a subclass of this class"""
COMPARE_DOC_MAPPING = {
    'herald': COMPARE_DOC_HERALD,
    'desc': COMPARE_DOC_DESC,
    'compLimits': COMPARE_DOC_LIMITS,
    'sigma': COMPARE_DOC_SIGMA,
    'compTypeErr': COMPARE_DOC_TYPE_ERR,
}

COMPARE_FAIL_MSG = "Values {desc0} and {desc1} are not identical:\n\t"
COMPARE_WARN_MSG = ("Values {desc0} and {desc1} are not identical, but within "
                    "tolerances:\n\t")
COMPARE_PASS_MSG = "Values {desc0} and {desc0} are identical:\n\t"


def compareDocDecorator(f):
    """Decorator that updates doc strings for comparison methods.

    Similar to :func:`serpentTools.plot.magicPlotDocDecorator`
    but for comparison functions
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    doc = dedent(f.__doc__)
    for magic, replace in iteritems(COMPARE_DOC_MAPPING):
        lookF = '{' + magic + '}'
        if lookF in doc:
            doc = doc.replace(lookF, dedent(replace))
    decorated.__doc__ = doc
    return decorated


def _getDefDescs(desc0, desc1):
    desc0 = desc0 if desc0 is not None else 'first'
    desc1 = desc1 if desc1 is not None else 'second'
    return desc0, desc1


@compareDocDecorator
def getCommonKeys(d0, d1, desc0='first', desc1='second', herald=error):
    """
    Return a set of common keys from two dictionaries

    Also supports printing warning messages for keys not
    found on one collection.

    If ``d0`` and ``d1`` are :class:`dict`, then the
    keys will be obtained with ``d1.keys()``. Otherwise,
    assume we have an iterable of keys and convert to
    :class:`set`.

    Parameters
    ----------
    d0: dict or iterable
    d1: dict or iterable
        Dictionary of keys or iterable of keys to be compared
    {desc}
    {herald}
    Returns
    -------
    set:
        Keys found in both ``d{{0, 1}}``
    """
    k0 = d0.keys() if isinstance(d0, dict) else d0
    k1 = d1.keys() if isinstance(d1, dict) else d1
    s0 = set(k0)
    s1 = set(k1)

    common = s0.intersection(s1)
    missing = s0.symmetric_difference(s1)
    if missing:
        in0 = s0.difference(s1)
        in1 = s1.difference(s0)
        logMissingKeys(desc0, desc1, in0, in1, herald)
    return common


COMPARE_NUMERICS = float, int


@compareDocDecorator
def directCompare(obj0, obj1, lower, upper, quantity):
    """
    Return True if values are close enough to each other.

    Wrapper around various comparision tests for strings, numeric, and
    arrays.

    The failing values will be appended to the next line of the error message

    Parameters
    ----------
    obj0: str or float or int or :class:`numpy.ndarray`
    obj1: str or float or int or :class:`numpy.ndarray`
        Objects to compare
    {compLimits}
    quantity: str
        Description of the value being compared. Will be
        used to notify the user about any differences

    Returns
    -------
    bool:
        If the values are close enough as determined by the settings.

    Raises
    ------
    TypeError:
        If the object types are not supported. This means the developers
        need to either extend this to meet the type, or use a different
        test function.
    """
    type0 = type(obj0)
    type1 = type(obj1)
    noticeTuple = [obj0, obj1, quantity]
    if ((type0 not in COMPARE_NUMERICS or type1 not in COMPARE_NUMERICS) 
            and type0 != type(obj1)):
        differentTypes(type0, type1, quantity)
        return False
    if type0 is str:
        if obj0 != obj1:
            notIdentical(*noticeTuple)
            return False
        identical(*noticeTuple)
        return True

    if type0 in (float, int, ndarray):
        diff = fabs(obj0 - obj1) * 100
        if type0 is ndarray:
            nonZI = where(obj0 > LOWER_LIM_DIVISION)
            diff[nonZI] /= obj0[nonZI]
        elif obj0 > LOWER_LIM_DIVISION:
            diff /= obj0
        maxDiff = diff.max() if isinstance(diff, ndarray) else diff
        if maxDiff < LOWER_LIM_DIVISION:
            identical(*noticeTuple)
            return True
        if maxDiff <= lower:
            acceptableLow(*noticeTuple)
            return True
        if maxDiff >= upper:
            outsideTols(*noticeTuple)
            return False
        acceptableHigh(*noticeTuple)
        return True
    raise TypeError(
          "directCompare is not configured to make tests on objects of type "
          "{tp}\n\tUsers: Create a issue on GitHub to alert developers."
          "\n\tDevelopers: Update this function or create a compare function "
          "for {tp} objects.".format(tp=type0))

def getKeyMatchingShapes(keySet, map0, map1, desc0='first', desc1='second'):
    """
    Return a set of keys in map0/1 that point to arrays with identical shapes.

    Parameters
    ----------
    keySet: set or list or tuple or iterable
        Iterable container with keys that exist in map0 and map1. The contents
        of ``map0/1`` under these keys will be compared
    map0: dict
    map1: dict
        Two dictionaries containing at least all the keys in ``keySet``. 
        Objects under keys in ``keySet`` will have their sizes compared if 
        they are :class:`numpy.ndarray`. Non-arrays will be included only 
        if their types are identical
    desc0: str
    decs1: str
        Descriptions of the two dictionaries being compared. Used to alert the user
        to the shortcomings of the two dictionaries

    Returns
    -------
    set:
        Set of all keys that exist in both dictionaries and are either
        identical types, or are arrays of identical size
    """
    missing = {0: set(), 1: set()}
    badTypes = {}
    badShapes = {}
    goodKeys = set()
    for key in keySet:
        if key not in map0 or key not in map1:
            for mapD, misK in zip((map0, map1), (0, 1)):
                if key not in mapD:
                    missing[misK].add(key)
            continue
        v0 = map0[key]
        v1 = map1[key]
        t0 = type(v0)
        t1 = type(v1)
        if t0 != t1:
            badTypes[key] = (t0, t1)
            continue
        if t0 is ndarray:
            if v0.shape != v1.shape:
                badShapes[key] = (v0.shape, v1.shape)
                continue
        goodKeys.add(key)

    # raise some messages
    if any(missing[0]) or any(missing[1]):
        logMissingKeys(desc0, desc1, missing[0], missing[1])
    if badTypes:
        logBadTypes(desc0, desc1, badTypes)
    if badShapes:
        logBadShapes(desc0, desc1, badShapes)
    return goodKeys
