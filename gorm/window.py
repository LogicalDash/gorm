from collections import defaultdict, MutableMapping
try:
    from numpy import array, less_equal, greater
    have_numpy = True
except ImportError:
    have_numpy = False


def window_left(revs, rev):
    k = frozenset(revs)
    if k not in window_left.memo or rev not in window_left.memo[k]:
        if have_numpy:
            revs = array(tuple(k))
            smalls = revs[less_equal(revs, rev)]
            if len(smalls):
                window_left.memo[k][rev] = smalls.max()
            else:
                window_left.memo[k][rev] = None
        else:
            smalls = [rv for rv in revs if rv < rev]
            if smalls:
                window_left.memo[k][rev] = max(smalls)
            else:
                window_left.memo[k][rev] = None
    return window_left.memo[k][rev]
window_left.memo = defaultdict(dict)


def window_right(revs, rev):
    k = frozenset(revs)
    if k not in window_right.memo or rev not in window_right.memo[k]:
        if have_numpy:
            revs = array(tuple(k))
            bigs = revs[greater(revs, rev)]
            if len(bigs):
                window_right.memo[k][rev] = bigs.min()
            else:
                window_right.memo[k][rev] = None
        else:
            bigs = [rv for rv in revs if rv > rev]
            if bigs:
                window_right.memo[k][rev] = min(bigs)
            else:
                window_right.memo[k][rev] = None
    return window_right.memo[k][rev]
window_right.memo = defaultdict(dict)


def window(revs, rev):
    return (
        window_left(revs, rev),
        window_right(revs, rev)
    )


class WindowDict(MutableMapping):
    def __init__(self):
        self._real = {}

    def __iter__(self):
        return iter(self._real)

    def __len__(self):
        return len(self._real)

    def __setitem__(self, k, v):
        self._real[k] = v

    def __delitem__(self, k):
        del self._real[k]

    def __getitem__(self, k):
        if k in self._real:
            return self._real[k]
        try:
            return self._real[
                window_left(self._real.keys(), k)
            ]
        except ValueError:
            raise KeyError(
                "Key {} not set, nor any before it.".format(k)
            )
