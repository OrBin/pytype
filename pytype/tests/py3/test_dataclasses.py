"""Tests for the dataclasses overlay."""

from pytype.tests import test_base


class TestDataclass(test_base.TargetPython3FeatureTest):
  """Tests for @dataclass."""

  def test_basic(self):
    ty = self.Infer("""
      import dataclasses
      @dataclasses.dataclass
      class Foo(object):
        x: bool
        y: int
        z: str
    """)
    self.assertTypesMatchPytd(ty, """
      dataclasses: module
      class Foo(object):
        x: bool
        y: int
        z: str
        def __init__(self, x: bool, y: int, z: str) -> None: ...
    """)

  def test_late_annotations(self):
    ty = self.Infer("""
      import dataclasses
      @dataclasses.dataclass
      class Foo(object):
        x: 'Foo'
        y: str
    """)
    self.assertTypesMatchPytd(ty, """
      dataclasses: module
      class Foo(object):
        x: Foo
        y: str
        def __init__(self, x: Foo, y: str) -> None: ...
    """)

  def test_redefine(self):
    """The first annotation should determine the order."""
    ty = self.Infer("""
      import dataclasses
      @dataclasses.dataclass
      class Foo(object):
        x: int
        y: int
        x: str = 'hello'
        y = 10
    """)
    self.assertTypesMatchPytd(ty, """
      dataclasses: module
      class Foo(object):
        y: int
        x: str
        def __init__(self, x: str = ..., y: int = ...) -> None: ...
    """)

  def test_redefine_as_method(self):
    # NOTE: This arguably does the wrong thing, but it is what dataclass
    # actually does. We might want to make it an error.
    ty = self.Infer("""
      import dataclasses
      @dataclasses.dataclass
      class Foo(object):
        x: str = 'hello'
        y: int = 10
        def x(self):
          return 10
    """)
    self.assertTypesMatchPytd(ty, """
      from typing import Callable
      dataclasses: module
      class Foo(object):
        y: int
        def __init__(self, x: Callable = ..., y: int = ...) -> None: ...
        def x(self) -> int: ...
    """)

  def test_no_init(self):
    ty = self.Infer("""
      import dataclasses
      @dataclasses.dataclass(init=False)
      class Foo(object):
        x: bool
        y: int
        z: str
    """)
    self.assertTypesMatchPytd(ty, """
      dataclasses: module
      class Foo(object):
        x: bool
        y: int
        z: str
    """)

  def test_field(self):
    ty = self.Infer("""
      from typing import List
      import dataclasses
      @dataclasses.dataclass()
      class Foo(object):
        x: bool = dataclasses.field(default=True)
        y: List[int] = dataclasses.field(default_factory=list)
    """)
    self.assertTypesMatchPytd(ty, """
      from typing import List
      dataclasses: module
      class Foo(object):
        x: bool
        y: List[int]
        def __init__(self, x: bool = ..., y: List[int] = ...) -> None: ...
    """)

  def test_type_mismatch(self):
    err = self.CheckWithErrors("""
      import dataclasses
      @dataclasses.dataclass()
      class Foo(object):
        x: bool = 10
    """)
    self.assertErrorLogIs(err, [(4, "annotation-type-mismatch")])

  def test_field_type_mismatch(self):
    err = self.CheckWithErrors("""
      import dataclasses
      @dataclasses.dataclass()
      class Foo(object):
        x: bool = dataclasses.field(default=10)
    """)
    self.assertErrorLogIs(err, [(4, "annotation-type-mismatch")])

  def test_factory_type_mismatch(self):
    err = self.CheckWithErrors("""
      import dataclasses
      @dataclasses.dataclass()
      class Foo(object):
        x: bool = dataclasses.field(default_factory=set)
    """)
    self.assertErrorLogIs(err, [(4, "annotation-type-mismatch")])

  def test_field_no_init(self):
    ty = self.Infer("""
      import dataclasses
      @dataclasses.dataclass()
      class Foo(object):
        x: bool = dataclasses.field(default=True)
        y: int = dataclasses.field(init=False)
    """)
    self.assertTypesMatchPytd(ty, """
      dataclasses: module
      class Foo(object):
        x: bool
        y: int
        def __init__(self, x: bool = ...) -> None: ...
    """)

  def test_field_init_no_default(self):
    ty = self.Infer("""
      import dataclasses
      @dataclasses.dataclass()
      class Foo(object):
        x: bool = dataclasses.field()
        y: int
    """)
    self.assertTypesMatchPytd(ty, """
      dataclasses: module
      class Foo(object):
        x: bool
        y: int
        def __init__(self, x: bool, y: int) -> None: ...
    """)

  def test_bad_default_param_order(self):
    err = self.CheckWithErrors("""
      import dataclasses
      @dataclasses.dataclass()
      class Foo(object):
        x: int = 10
        y: str
    """)
    self.assertErrorLogIs(err, [(4, "invalid-function-definition")])

  def test_any(self):
    self.Check("""
      import dataclasses
      from typing import Any

      @dataclasses.dataclass
      class Foo(object):
        foo: Any = None
    """)

  def test_instantiate_field_type(self):
    self.Check("""
      import dataclasses
      @dataclasses.dataclass
      class Foo(object):
        def foo(self):
          for field in dataclasses.fields(self):
            field.type()
    """)

  def test_subclass(self):
    ty = self.Infer("""
      import dataclasses
      @dataclasses.dataclass()
      class Foo(object):
        w: float
        x: bool = dataclasses.field(default=True)
        y: int = dataclasses.field(init=False)
      class Bar(Foo):
        def get_w(self):
          return self.w
        def get_x(self):
          return self.x
        def get_y(self):
          return self.y
    """)
    self.assertTypesMatchPytd(ty, """
      dataclasses: module
      class Foo(object):
        w: float
        x: bool
        y: int
        def __init__(self, w: float, x: bool = ...) -> None: ...
      class Bar(Foo):
        def get_w(self) -> float: ...
        def get_x(self) -> bool : ...
        def get_y(self) -> int: ...
    """)

  def test_use_late_annotation(self):
    self.Check("""
      import dataclasses
      from typing import Optional

      @dataclasses.dataclass
      class Foo:
        foo: Optional['Foo'] = None

      @dataclasses.dataclass
      class Bar:
        bar: Foo = dataclasses.field(default_factory=Foo)
    """)

  def test_union(self):
    self.Check("""
      import dataclasses
      from typing import Optional
      @dataclasses.dataclass
      class Foo:
        foo: Optional[str] = ''
    """)

  def test_reuse_attribute_name(self):
    self.Check("""
      import dataclasses
      from typing import Optional

      @dataclasses.dataclass
      class Foo:
        x: Optional[str] = None

      @dataclasses.dataclass
      class Bar:
        x: str
    """)


test_base.main(globals(), __name__ == "__main__")
