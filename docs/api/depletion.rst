.. _depletion:

================
Depletion Reader
================

.. warning::

    Does not support depleted materials with underscores,
    i.e. ``fuel_1`` will not be matched with the current methods.
    Follow up on, or claim, the issue on GitHub: :issue:`58`

.. autoclass:: serpentTools.parsers.depletion.DepletionReader
    :special-members: __getitem__

