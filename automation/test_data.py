"""测试运行时记录的业务数据（账号、订单等）"""
from __future__ import annotations

from typing import Any


class TestData:
    """用例内通过 test_data 记录的数据，运行结束后写入 artifacts 并在 UI 展示。"""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        if value is not None and value != "":
            self._data[key] = value

    def update(self, values: dict[str, Any]) -> None:
        for key, value in values.items():
            self.set(key, value)

    def record_auth(
        self,
        *,
        action: str,
        email: str,
        password: str,
        customer_id: str | None = None,
    ) -> None:
        self.update({
            "action": action,
            "email": email,
            "password": password,
            "customer_id": customer_id,
        })

    def record_order(
        self,
        *,
        order_id: str,
        email: str | None = None,
        **extra: Any,
    ) -> None:
        self.set("action", extra.pop("action", "order"))
        self.set("order_id", order_id)
        if email:
            self.set("email", email)
        self.update(extra)

    def to_dict(self) -> dict[str, Any]:
        return dict(self._data)

    def __bool__(self) -> bool:
        return bool(self._data)
