"""GBNF grammar generator for Pydantic v2 models.

Converts Pydantic model field types into GBNF grammar strings that
can be passed to Ollama's ``format`` parameter to constrain LLM output.
"""

import typing
from typing import Any, Dict, List, Optional, Type, get_origin, get_args

from pydantic import BaseModel


def _resolve_type(tp: Type[Any]) -> Type[Any]:
    """Unwrap Optional / Union[..., None] to get the inner type."""
    origin = get_origin(tp)
    if origin is Optional or (origin is typing.Union and type(None) in get_args(tp)):
        args = get_args(tp)
        non_none = [a for a in args if a is not type(None)]
        if non_none:
            return _resolve_type(non_none[0])
    return tp


def _type_name(tp: Type[Any]) -> str:
    tp = _resolve_type(tp)
    origin = get_origin(tp)
    if origin is list or origin is List:
        return "array"
    if origin is dict or origin is Dict:
        return "object"
    if tp is str:
        return "string"
    if tp is int:
        return "integer"
    if tp is float:
        return "number"
    if tp is bool:
        return "boolean"
    if isinstance(tp, type) and issubclass(tp, BaseModel):
        return tp.__name__
    return "string"


def _collect_models(model_class: Type[BaseModel]) -> List[Type[BaseModel]]:
    """BFS over nested BaseModel fields. Returns list in visit order."""
    seen: set = set()
    result: List[Type[BaseModel]] = []
    queue: List[Type[BaseModel]] = [model_class]

    while queue:
        cls = queue.pop(0)
        if cls.__name__ in seen:
            continue
        seen.add(cls.__name__)
        result.append(cls)

        for finfo in cls.model_fields.values():
            tp = _resolve_type(finfo.annotation)
            origin = get_origin(tp)
            if origin is list or origin is List:
                args = get_args(tp)
                if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
                    queue.append(args[0])
            elif origin is dict or origin is Dict:
                continue
            elif isinstance(tp, type) and issubclass(tp, BaseModel):
                queue.append(tp)

    return result


def gbnf_schema(model_class: Type[BaseModel]) -> str:
    """Generate a GBNF grammar string from a Pydantic v2 model.

    The returned grammar can be passed to Ollama's ``format`` parameter.
    Handles ``str``, ``int``, ``float``, ``bool``, ``Optional``,
    ``List[T]``, ``Dict[str, Any]``, and nested ``BaseModel`` sub‑fields.

    Parameters
    ----------
    model_class:
        A Pydantic v2 ``BaseModel`` subclass.

    Returns
    -------
    str
        A GBNF grammar definition.
    """
    all_models = _collect_models(model_class)
    lines: List[str] = []

    for cls in all_models:
        cls_name = cls.__name__
        field_lines: List[str] = []

        for fname, finfo in cls.model_fields.items():
            tp = _resolve_type(finfo.annotation)
            origin = get_origin(tp)

            if isinstance(tp, type) and issubclass(tp, BaseModel):
                field_lines.append("  \"\\\"%s\\\"\" ws \":\" ws %s" % (fname, tp.__name__))
                continue

            if origin is list or origin is List:
                args = get_args(tp)
                if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
                    field_lines.append("  \"\\\"%s\\\"\" ws \":\" ws %s-list" % (fname, cls_name))
                else:
                    field_lines.append("  \"\\\"%s\\\"\" ws \":\" ws array" % fname)
                continue

            if origin is dict or origin is Dict:
                field_lines.append("  \"\\\"%s\\\"\" ws \":\" ws object" % fname)
                continue

            target = _type_name(tp)
            field_lines.append("  \"\\\"%s\\\"\" ws \":\" ws %s" % (fname, target))

        lines.append("")
        lines.append("%s ::= \"{\" ws %s-fields ws \"}\"" % (cls_name, cls_name))
        lines.append("%s-fields ::= %s-field (\",\" ws %s-field)*" % (cls_name, cls_name, cls_name))
        lines.append("%s-field ::=" % cls_name)
        lines.append(" |".join(field_lines))
        lines.append("")

    for cls in all_models:
        for finfo in cls.model_fields.values():
            tp = _resolve_type(finfo.annotation)
            origin = get_origin(tp)
            if origin is list or origin is List:
                args = get_args(tp)
                if args and isinstance(args[0], type) and issubclass(args[0], BaseModel):
                    item_name = args[0].__name__
                    list_rule = "%s-list ::= \"[\" ws \"]\" | \"[\" ws %s (\",\" ws %s)* ws \"]\"" % (
                        cls.__name__, item_name, item_name,
                    )
                    if list_rule not in lines:
                        lines.append(list_rule)

    lines.extend([
        "string ::= \"\\\"\" [^\"]* \"\\\"\"",
        "integer ::= [0-9]+",
        "number ::= [0-9]+ \".\"? [0-9]*",
        "boolean ::= \"true\" | \"false\"",
        "array ::= \"[\" ws \"]\" | \"[\" ws string (\",\" ws string)* ws \"]\"",
        "object ::= \"{\" ws (string \":\" ws string (\",\" ws string \":\" ws string)*)? ws \"}\"",
        "ws ::= [ \\t\\n]*",
    ])

    root_line = "root ::= %s" % model_class.__name__
    return root_line + "\n" + "\n".join(lines)
