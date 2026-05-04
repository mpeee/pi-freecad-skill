#!/usr/bin/env python3
"""
Script Library Unit Tests — tests save/load/list/find/delete logic
using a temporary directory. No FreeCAD, no pi, no TCP needed.
"""

import sys
import os
import json
import tempfile
import shutil
from pathlib import Path

PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"
results = {"pass": 0, "fail": 0}

# ── Replicate the script library helpers from freecad.ts in Python ────────────

INDEX_FILE = "_index.json"


def slugify(name: str) -> str:
    import re
    return re.sub(r"^_|_$", "", re.sub(r"[^a-z0-9]+", "_", name.lower()))


def load_index(directory: str) -> list:
    p = Path(directory) / INDEX_FILE
    if not p.exists():
        return []
    return json.loads(p.read_text())


def save_index(directory: str, index: list):
    p = Path(directory) / INDEX_FILE
    p.write_text(json.dumps(index, indent=2))


def save_script(name, description, code, scope, cwd, tmp_global):
    directory = str(Path(cwd) / "fc-scripts") if scope == "project" else tmp_global
    Path(directory).mkdir(parents=True, exist_ok=True)
    slug = slugify(name)
    filepath = Path(directory) / f"{slug}.py"
    filepath.write_text(code)
    index = load_index(directory)
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    existing = next((i for i, e in enumerate(index) if e["name"] == slug), -1)
    entry = {"name": slug, "description": description, "file": f"{slug}.py",
             "scope": scope, "created": now if existing < 0 else index[existing]["created"],
             "modified": now}
    if existing >= 0:
        index[existing] = entry
    else:
        index.append(entry)
    save_index(directory, index)
    return slug


def find_script(name, cwd, tmp_global):
    slug = slugify(name)
    for scope, directory in [("project", str(Path(cwd) / "fc-scripts")),
                              ("global", tmp_global)]:
        index = load_index(directory)
        entry = next((e for e in index if e["name"] == slug), None)
        if entry:
            fp = Path(directory) / entry["file"]
            if fp.exists():
                return {"entry": entry, "code": fp.read_text(), "scope": scope}
    return None


def list_all(cwd, tmp_global):
    seen = set()
    results = []
    for scope, directory in [("project", str(Path(cwd) / "fc-scripts")),
                              ("global", tmp_global)]:
        for e in load_index(directory):
            if e["name"] not in seen:
                seen.add(e["name"])
                results.append({**e, "scope": scope})
    return results


def delete_script(name, cwd, tmp_global, scope=None):
    slug = slugify(name)
    scopes = [scope] if scope else ["project", "global"]
    for s in scopes:
        directory = str(Path(cwd) / "fc-scripts") if s == "project" else tmp_global
        index = load_index(directory)
        idx = next((i for i, e in enumerate(index) if e["name"] == slug), -1)
        if idx >= 0:
            fp = Path(directory) / index[idx]["file"]
            if fp.exists():
                fp.unlink()
            index.pop(idx)
            save_index(directory, index)
            return True
    return False


# ── Test helpers ─────────────────────────────────────────────────────────────

def check(name: str, condition: bool, detail: str = ""):
    sym = PASS if condition else FAIL
    suffix = f"  [{detail}]" if detail and not condition else ""
    print(f"  {sym} {name}{suffix}")
    results["pass" if condition else "fail"] += 1


def section(title: str):
    print(f"\n── {title} {'─' * (46 - len(title))}")


# ── Setup ─────────────────────────────────────────────────────────────────────
tmp = tempfile.mkdtemp(prefix="fc_test_")
cwd = Path(tmp) / "project"
cwd.mkdir()
tmp_global = str(Path(tmp) / "global")
Path(tmp_global).mkdir()

try:
    # ── T01 Slugify ───────────────────────────────────────────────────────────
    section("T01 — slugify")
    check("snake_case unchanged",    slugify("my_script") == "my_script")
    check("spaces to underscores",   slugify("My Script") == "my_script")
    check("mixed case",              slugify("PartBoxHoles") == "partboxholes")
    check("special chars stripped",  slugify("part-box--holes!") == "part_box_holes")
    check("leading/trailing removed",slugify("_foo_") == "foo")

    # ── T02 Save & Find ───────────────────────────────────────────────────────
    section("T02 — save & find")
    save_script("TestBox", "A test box script", "print('hello box')", "project", str(cwd), tmp_global)
    found = find_script("TestBox", str(cwd), tmp_global)
    check("script found after save",       found is not None)
    check("code matches",                  found and "hello box" in found["code"])
    check("scope is project",             found and found["scope"] == "project")
    check("slug applied to name",          found and found["entry"]["name"] == "testbox")
    check("file exists on disk",
          (cwd / "fc-scripts" / "testbox.py").exists())

    # ── T03 Overwrite ─────────────────────────────────────────────────────────
    section("T03 — overwrite")
    save_script("TestBox", "Updated description", "print('updated')", "project", str(cwd), tmp_global)
    found2 = find_script("TestBox", str(cwd), tmp_global)
    check("overwrite preserves name",     found2 and found2["entry"]["name"] == "testbox")
    check("code updated",                 found2 and "updated" in found2["code"])
    check("description updated",          found2 and "Updated" in found2["entry"]["description"])
    check("created timestamp preserved",  found2 and found and
          found2["entry"]["created"] == found["entry"]["created"])
    index = load_index(str(cwd / "fc-scripts"))
    check("only one entry in index",      len(index) == 1)

    # ── T04 Global scope ──────────────────────────────────────────────────────
    section("T04 — global scope")
    save_script("SharedUtil", "Cross-project utility", "print('global')", "global", str(cwd), tmp_global)
    found_g = find_script("SharedUtil", str(cwd), tmp_global)
    check("global script found",          found_g is not None)
    check("global scope reported",        found_g and found_g["scope"] == "global")
    check("file in global dir",           (Path(tmp_global) / "sharedutil.py").exists())

    # ── T05 Precedence ────────────────────────────────────────────────────────
    section("T05 — project takes precedence over global")
    save_script("SharedUtil", "Project override", "print('project override')", "project", str(cwd), tmp_global)
    found_p = find_script("SharedUtil", str(cwd), tmp_global)
    check("project version found",        found_p and found_p["scope"] == "project")
    check("project code returned",        found_p and "project override" in found_p["code"])

    # ── T06 List all (dedup) ──────────────────────────────────────────────────
    section("T06 — list all with deduplication")
    scripts = list_all(str(cwd), tmp_global)
    names = [s["name"] for s in scripts]
    check("testbox in list",              "testbox" in names)
    check("sharedutil in list",           "sharedutil" in names)
    check("no duplicates",               len(names) == len(set(names)))
    # sharedutil exists in both scopes — should appear only once as "project"
    su = next((s for s in scripts if s["name"] == "sharedutil"), None)
    check("sharedutil as project scope",  su and su["scope"] == "project")

    # ── T07 List by scope ─────────────────────────────────────────────────────
    section("T07 — list by scope (no dedup)")
    proj_dir = str(cwd / "fc-scripts")
    proj_only = load_index(proj_dir)
    glob_only = load_index(tmp_global)
    proj_names = [e["name"] for e in proj_only]
    glob_names = [e["name"] for e in glob_only]
    check("project dir has testbox",      "testbox" in proj_names)
    check("project dir has sharedutil",   "sharedutil" in proj_names)
    check("global dir has sharedutil",    "sharedutil" in glob_names)
    check("global dir has no testbox",    "testbox" not in glob_names)

    # ── T08 Delete ────────────────────────────────────────────────────────────
    section("T08 — delete")
    ok = delete_script("testbox", str(cwd), tmp_global)
    check("delete returns True",          ok)
    check("testbox gone from index",      find_script("testbox", str(cwd), tmp_global) is None)
    check("file removed from disk",       not (cwd / "fc-scripts" / "testbox.py").exists())

    ok2 = delete_script("nonexistent", str(cwd), tmp_global)
    check("delete nonexistent returns False", not ok2)

    # ── T09 Index integrity ───────────────────────────────────────────────────
    section("T09 — index integrity")
    # File exists but not in index → findScript should not find it
    orphan = cwd / "fc-scripts" / "orphan.py"
    orphan.write_text("print('orphan')")
    found_orphan = find_script("orphan", str(cwd), tmp_global)
    check("orphan file not found (index is source of truth)", found_orphan is None)

finally:
    shutil.rmtree(tmp)

# ── Summary ───────────────────────────────────────────────────────────────────
total = results["pass"] + results["fail"]
print(f"\nResults: {results['pass']}/{total} passed"
      + (f"  ({results['fail']} failed)" if results["fail"] else "  ✓ all passed"))
sys.exit(0 if results["fail"] == 0 else 1)
