from collections.abc import MutableMapping


VALUE = object()


class Paths(MutableMapping):

    def __init__(self):
        self._data = {}

    def __getitem__(self, path):
        data = self._data
        for key in path:
            data = data[key]
        return data[VALUE]

    def __setitem__(self, path, value):
        data = self._data
        for key in path:
            data = data.setdefault(key, {})
        data[VALUE] = value

    def __delitem__(self, path):
        data = self._data
        stack = []

        for key in path:
            stack.append(data)
            data = data[key]

        del data[VALUE]

        while not data and stack:
            data = stack.pop()
            del data[path[len(stack)]]

    def items(self):
        try:
            value = self._data[VALUE]
        except KeyError:
            pass
        else:
            yield (), value
        
        stack = [((), iter(self._data.items()))]

        while stack:
            path, items = stack[-1]
            try:
                key, value = next(items)
            except StopIteration:
                stack.pop()
                continue
            if key is VALUE:
                continue

            subpath = (*path, key)
            try:
                subvalue = value[VALUE]
            except KeyError:
                pass
            else:
                yield subpath, subvalue
            stack.append((subpath, iter(value.items())))
        
    def __iter__(self):
        for key, _ in self.items():
            yield key

    def values(self):
        for _, value in self.items():
            yield value

    def __len__(self):
        res = 0
        for _ in self.items():
            res += 1
        return res

    def clear(self):
        self._data.clear()

    def poptree(self, path):
        try:
            *path, last_key = path
        except ValueError:
            res = Paths()
            res._data = self._data
            self._data = {}
            return res

        stack = []
        data = self._data
        try:
            for key in path:
                stack.append(data)
                data = data[key]
            popped = data.pop(last_key)
        except KeyError:
            return Paths()

        while not data and stack:
            data = stack.pop()
            del data[path[len(stack)]]

        res = Paths()
        res._data = popped
        return res
