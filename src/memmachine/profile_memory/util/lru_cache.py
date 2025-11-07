from typing import Any


class Node:
    """
    双向链表的节点。
    每个节点存储一个键值对。
    """

    def __init__(self, key: Any, value: Any):
        self.key = key
        self.value = value
        self.prev: Node | None = None
        self.next: Node | None = None


class LRUCache:
    """
    最近最少使用（LRU）缓存的实现。

    属性:
        capacity (int): 缓存可以容纳的最大项目数。
        cache (dict): 将键映射到节点对象的字典，用于 O(1) 查找。
        head (Node): 双向链表的哨兵头节点。
        tail (Node): 双向链表的哨兵尾节点。
    """

    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("Capacity must be a positive integer")
        self.capacity = capacity
        self.cache: dict[Any, Any] = {}  # 存储 key -> Node

        # 初始化双向链表的哨兵头节点和尾节点。
        # head.next 指向最近使用的项目。
        # tail.prev 指向最近最少使用的项目。
        self.head = Node(None, None)
        self.tail = Node(None, None)
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove_node(self, node: Node) -> None:
        """从双向链表中移除一个节点。"""
        if node.prev and node.next:
            prev_node = node.prev
            next_node = node.next
            prev_node.next = next_node
            next_node.prev = prev_node

    def _add_to_front(self, node: Node) -> None:
        """将节点添加到双向链表的前端（紧跟在 head 之后）。"""
        node.prev = self.head
        node.next = self.head.next
        if self.head.next:
            self.head.next.prev = node
        self.head.next = node

    def erase(self, key: Any) -> None:
        """
        从缓存中移除一个项目。
        """
        if key in self.cache:
            node = self.cache[key]
            self._remove_node(node)
            del self.cache[key]

    def get(self, key: Any) -> Any:
        """
        从缓存中检索一个项目。
        如果键存在则返回其值，否则返回 None（或抛出 KeyError）。
        将被访问的项目移到前端（标记为最近使用）。
        """
        if key in self.cache:
            node = self.cache[key]
            # 将被访问的节点移到前端
            self._remove_node(node)
            self._add_to_front(node)
            return node.value
        return None

    def put(self, key: Any, value: Any) -> None:
        """
        在缓存中添加或更新一个项目。
        如果键存在，则更新其值并将其移到前端。
        如果键不存在，则添加它。
        如果缓存已满，则驱逐最近最少使用的项目。
        """
        if key in self.cache:
            # 更新现有键的值并将其移到前端
            node = self.cache[key]
            node.value = value
            self._remove_node(node)
            self._add_to_front(node)
        else:
            # 添加新键
            if len(self.cache) >= self.capacity:
                # 缓存已满，驱逐最近最少使用的项目（从 tail.prev）
                if (
                    self.tail.prev and self.tail.prev != self.head
                ):  # 确保有项目可以驱逐
                    lru_node = self.tail.prev
                    self._remove_node(lru_node)
                    del self.cache[lru_node.key]

            new_node = Node(key, value)
            self.cache[key] = new_node
            self._add_to_front(new_node)
