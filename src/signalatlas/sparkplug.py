"""Minimal, wire-compatible Sparkplug B protobuf subset for synthetic Node metrics.

The descriptors mirror the field numbers/wire types of Eclipse Tahu's Payload
(schema package org.eclipse.tahu.protobuf). This implements only scalar metrics,
not the full specification or device/template/dataset model. It is NOT a claim of
Sparkplug TCK certification. Transport/session requirements are in edge.py.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from google.protobuf import descriptor_pb2, descriptor_pool, message_factory

DT_INT64 = 4
DT_DOUBLE = 10
DT_BOOLEAN = 11
DT_STRING = 12


def _message_class():
    file = descriptor_pb2.FileDescriptorProto()
    file.name = "signalatlas_sparkplug_subset.proto"
    file.package = "org.eclipse.tahu.protobuf"
    file.syntax = "proto2"
    payload = file.message_type.add()
    payload.name = "Payload"
    metric = payload.nested_type.add()
    metric.name = "Metric"
    oneof = metric.oneof_decl.add()
    oneof.name = "value"

    def add(msg, name, number, typ, label=1, type_name="", oneof_index=None):
        f = msg.field.add()
        f.name, f.number, f.type, f.label = name, number, typ, label
        if type_name:
            f.type_name = type_name
        if oneof_index is not None:
            f.oneof_index = oneof_index

    add(metric, "name", 1, 9)
    add(metric, "alias", 2, 4)
    add(metric, "timestamp", 3, 4)
    add(metric, "datatype", 4, 13)
    add(metric, "int_value", 10, 13, oneof_index=0)
    add(metric, "long_value", 11, 4, oneof_index=0)
    add(metric, "float_value", 12, 2, oneof_index=0)
    add(metric, "double_value", 13, 1, oneof_index=0)
    add(metric, "boolean_value", 14, 8, oneof_index=0)
    add(metric, "string_value", 15, 9, oneof_index=0)
    add(payload, "timestamp", 1, 4)
    add(payload, "metrics", 2, 11, label=3,
        type_name=".org.eclipse.tahu.protobuf.Payload.Metric")
    add(payload, "seq", 3, 4)
    pool = descriptor_pool.DescriptorPool()
    pool.Add(file)
    return message_factory.GetMessageClass(
        pool.FindMessageTypeByName("org.eclipse.tahu.protobuf.Payload")
    )

Payload = _message_class()


@dataclass(frozen=True)
class Decoded:
    timestamp_ms: int
    seq: int | None
    metrics: dict[str, Any]


def encode(metrics: dict[str, Any], timestamp_ms: int, seq: int | None = None) -> bytes:
    payload = Payload()
    payload.timestamp = timestamp_ms
    if seq is not None:
        if not 0 <= seq <= 255:
            raise ValueError("Sparkplug sequence must be 0..255")
        payload.seq = seq
    for name, value in metrics.items():
        m = payload.metrics.add()
        m.name = name
        m.timestamp = timestamp_ms
        if isinstance(value, bool):
            m.datatype, m.boolean_value = DT_BOOLEAN, value
        elif isinstance(value, int):
            if not 0 <= value < 2**63:
                raise ValueError("Synthetic integers must be nonnegative signed 64-bit")
            m.datatype, m.long_value = DT_INT64, value
        elif isinstance(value, float):
            m.datatype, m.double_value = DT_DOUBLE, value
        elif isinstance(value, str):
            m.datatype, m.string_value = DT_STRING, value
        else:
            raise TypeError(f"Unsupported synthetic metric type: {name}")
    return payload.SerializeToString()


def decode(blob: bytes) -> Decoded:
    if not blob or len(blob) > 512_000:
        raise ValueError("Empty or oversized Sparkplug payload")
    payload = Payload()
    payload.ParseFromString(blob)
    if not payload.HasField("timestamp"):
        raise ValueError("Missing Sparkplug timestamp")
    metrics: dict[str, Any] = {}
    types = {DT_INT64: "long_value", DT_DOUBLE: "double_value",
             DT_BOOLEAN: "boolean_value", DT_STRING: "string_value"}
    for m in payload.metrics:
        if not m.HasField("name") or not m.HasField("datatype"):
            raise ValueError("Metric missing name/datatype")
        field = types.get(m.datatype)
        if field is None or m.WhichOneof("value") != field:
            raise ValueError(f"Unsupported/inconsistent metric {m.name}")
        if m.name in metrics:
            raise ValueError("Duplicate metric name")
        metrics[m.name] = getattr(m, field)
    return Decoded(timestamp_ms=payload.timestamp,
                   seq=payload.seq if payload.HasField("seq") else None,
                   metrics=metrics)


def topic(group: str, kind: str, node_id: str) -> str:
    if kind not in {"NBIRTH", "NDATA", "NDEATH", "NCMD"}:
        raise ValueError("Unsupported topic type")
    for segment in (group, node_id):
        if not segment or any(ch in segment for ch in "/+#"):
            raise ValueError("Invalid Sparkplug topic segment")
    return f"spBv1.0/{group}/{kind}/{node_id}"
