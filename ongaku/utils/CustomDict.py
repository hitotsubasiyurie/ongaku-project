from typing import Iterable


class CustomDict(dict):
    """
    自定义字典子类。
    支持：
    1. self.keys().index(key)
       keys() 方法返回可索引的列表对象

    2. self.keys()[index]

    3. self.path_get(keys)  
       多层键路径的嵌套字典取值。
    """

    class KeyList(list):
        """
        字典键的列表包装，使其支持索引与列表操作。
        """
        def __init__(self, iterable):
            super().__init__(iterable)

    def keys(self):
        return CustomDict.KeyList(super().keys())

    def path_get(self, path: Iterable[str], default=None):
        cur = self
        for key in path:
            if not isinstance(cur, dict):
                return default
            if key not in cur:
                return default
            cur = cur[key]
        return cur


from collections import OrderedDict


OrderedDict.keys().


