from __future__ import annotations

from pathlib import Path

from ecobio_daily.llm_cache import cache_key, read_cache, write_cache


def test_cache_key_stable_across_calls():
    msgs = [{"role": "user", "content": "hi"}]
    k1 = cache_key(model="m", messages=msgs, response_format=None, temperature=0.2)
    k2 = cache_key(model="m", messages=msgs, response_format=None, temperature=0.2)
    assert k1 == k2


def test_cache_key_changes_with_model():
    msgs = [{"role": "user", "content": "hi"}]
    k1 = cache_key(model="m1", messages=msgs, response_format=None, temperature=0.2)
    k2 = cache_key(model="m2", messages=msgs, response_format=None, temperature=0.2)
    assert k1 != k2


def test_cache_key_changes_with_messages():
    k1 = cache_key(
        model="m",
        messages=[{"role": "user", "content": "a"}],
        response_format=None,
        temperature=0.2,
    )
    k2 = cache_key(
        model="m",
        messages=[{"role": "user", "content": "b"}],
        response_format=None,
        temperature=0.2,
    )
    assert k1 != k2


def test_cache_key_changes_with_response_format():
    msgs = [{"role": "user", "content": "hi"}]
    k1 = cache_key(
        model="m", messages=msgs, response_format=None, temperature=0.2
    )
    k2 = cache_key(
        model="m", messages=msgs, response_format="json_object", temperature=0.2
    )
    assert k1 != k2


def test_cache_key_changes_with_temperature():
    msgs = [{"role": "user", "content": "hi"}]
    k1 = cache_key(model="m", messages=msgs, response_format=None, temperature=0.2)
    k2 = cache_key(model="m", messages=msgs, response_format=None, temperature=0.5)
    assert k1 != k2


def test_read_cache_returns_none_for_missing_file(tmp_path: Path):
    assert read_cache(tmp_path, "nope") is None


def test_write_then_read_cache_roundtrip(tmp_path: Path):
    write_cache(tmp_path, key="abc", value="hello world", model="m1")
    assert read_cache(tmp_path, "abc") == "hello world"


def test_write_cache_creates_missing_directory(tmp_path: Path):
    nested = tmp_path / "deep" / "subdir"
    write_cache(nested, key="abc", value="hi", model="m")
    assert (nested / "abc.json").exists()
