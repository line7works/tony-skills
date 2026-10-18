#!/usr/bin/python3
"""The fake programs of sunrise's local half (slice 2's lane tests). Standard library only; never the network.

    rise_tools.py <tool> <arguments ...>

A test puts a wrapper of each name (`git`, `npx`, `npm`, `uv`, `python3`, `riseadapter`) in a folder of its own fixture and
names that folder first among the fixture's system folders, so the runner finds these in place of any real program. Every
call is recorded, in the shape `fakeprov.py` records it, under `$HOME/.fakes/<tool>/calls.jsonl`, with `changing` true for a
call that writes a repository or a project. `plan.json` there tells a call what to do (`fail`, `dot_git`, `stale`,
`stray`).

    git ...                 recorded, then the system's own git (`/usr/bin/git`) with the same arguments: the test's own
                            temporary repository is real, so the frame's reads of it are real
    npx --yes create-next-app@latest . --yes --disable-git
    npm create --yes astro@latest -- . ...       npm create --yes @quick-start/electron@latest . -- ...
    npm init --yes          npm --prefix DIR run build          npm --prefix DIR pkg get name
                            the build writes the scaffold's documented output (`fake_build_output` in its package file,
                            one path or a list) and records each path it wrote in `wrote.jsonl`; with the plan entry `stray`
                            it also writes `next-env.d.ts` at the project's top, as a real Next.js build does
    uv init --vcs none --app .
    python3 -I -B FILE      runs nothing: answers the hello line where FILE stands
    riseadapter canary --work DIR    the canary: "same" where DIR/AGENTS.md stands (a plan entry may answer "differs")

Each scaffolder writes a small tree in its working folder, as the real one documents; none runs git. The Electron one, with
the plan entry `dot_git`, also makes a `.git` folder of its own there (R7: the frame publishes none of it, G21-4). The
Next.js one, with the plan entry `stale`, also leaves `.next/BUILD_ID` as an earlier build would have (R9).
"""
import json
import os
import sys

TOOL = sys.argv[1]
ARGV = sys.argv[2:]
HOME = os.environ.get("HOME", "")
ROOT = os.path.join(HOME, ".fakes", TOOL)


def load(path, default):
    try:
        with open(path) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def record(changing):
    os.makedirs(ROOT, exist_ok=True)
    counts = load(os.path.join(ROOT, "counts.json"), {})
    key = " ".join(ARGV[:2])
    counts[key] = nth = counts.get(key, 0) + 1
    with open(os.path.join(ROOT, "counts.json"), "w") as fh:
        json.dump(counts, fh)
    with open(os.path.join(ROOT, "calls.jsonl"), "a") as fh:
        fh.write(json.dumps({"tool": TOOL, "argv": ARGV, "cwd": os.getcwd(), "changing": changing, "nth": nth}, sort_keys=True) + "\n")
    plan = [p for p in load(os.path.join(ROOT, "plan.json"), []) if p.get("when") in (None, ARGV[0] if ARGV else None)]
    return plan[0] if plan else {}


def write(rel, text):
    """A file of the scaffold, made as a program makes one: by the mode its creating process allows (the runner's own)."""
    full = os.path.join(os.getcwd(), rel)
    os.makedirs(os.path.dirname(full) or ".", exist_ok=True)
    with open(full, "w") as fh:
        fh.write(text)


def package(name, output, scripts=True):
    doc = {"name": name, "version": "0.1.0", "private": True}
    if scripts:
        doc["scripts"] = {"dev": "fake dev", "build": "fake build"}
    doc["fake_build_output"] = output          # where this fake's own build writes its output (the scaffold's documented one)
    write("package.json", json.dumps(doc, indent=2) + "\n")


GITIGNORE = "node_modules/\n%s\n.env*\n.vercel\n"      # each scaffold's own build output lines, as its real one ignores them


def scaffold(kind, todo):
    if kind == "next":
        package("app", ".next/BUILD_ID")
        if todo.get("stale"):
            write(".next/BUILD_ID", "left by an earlier build\n")
        write("app/page.tsx", "export default function Page() { return null }\n")
        write(".gitignore", GITIGNORE % "/.next/\n/out/\nnext-env.d.ts")
        write("AGENTS.md", "<!-- BEGIN:nextjs-agent-rules -->\nThis is a fixture framework block.\n<!-- END:nextjs-agent-rules -->\n")
        write("CLAUDE.md", "@AGENTS.md\n")
    elif kind == "astro":
        package("site", ["dist/index.html", ".astro/types.d.ts"])
        write("src/pages/index.astro", "<h1>site</h1>\n")
        write(".gitignore", GITIGNORE % "dist/\n.astro/")
    elif kind == "electron":
        package("desktop", "out/main/index.js")
        write("src/main/index.js", "// main\n")
        write(".gitignore", GITIGNORE % "out/")
        if todo.get("dot_git"):
            # the scaffolder's own repository, made where it runs (R7): its folder at the top, a file deeper
            write(".git/HEAD", "ref: refs/heads/master\n")
            write(".git/config", "[fake]\n\tmadeby = the fake electron scaffolder\n")
            write("src/.git", "gitdir: elsewhere\n")
    elif kind == "npm":
        doc = {"name": os.path.basename(os.getcwd()) or "script", "version": "1.0.0"}
        write("package.json", json.dumps(doc, indent=2) + "\n")
    elif kind == "uv":
        write("pyproject.toml", "[project]\nname = \"script\"\nversion = \"0.1.0\"\n")
        write("main.py", "def main():\n    print(\"Hello from script!\")\n\n\nif __name__ == \"__main__\":\n    main()\n")
        write("README.md", "")


def answer(code=0, text=""):
    sys.stdout.write(text)
    sys.stdout.flush()
    sys.exit(code)


def main():
    if TOOL == "git":
        changing = bool(ARGV) and any(a in ("init", "add", "commit", "branch") for a in ARGV)
        record(changing)
        os.execv("/usr/bin/git", ["git"] + ARGV)
    if TOOL == "npx":
        todo = record(True)
        if todo.get("do") == "fail":
            answer(1, "failed\n")
        scaffold("next", todo)
        answer(0, "Success! Created app\n")
    if TOOL == "npm":
        if ARGV[:1] == ["create"]:
            todo = record(True)
            if todo.get("do") == "fail":
                answer(1, "failed\n")
            scaffold("electron" if any("electron" in a for a in ARGV) else "astro", todo)
            answer(0, "done\n")
        if ARGV[:1] == ["init"]:
            todo = record(True)
            scaffold("npm", todo)
            answer(0, "Wrote to package.json\n")
        if ARGV[:1] == ["--prefix"] and len(ARGV) >= 4:
            folder, rest = ARGV[1], ARGV[2:]
            todo = record(rest[:2] == ["run", "build"])
            doc = load(os.path.join(folder, "package.json"), None)
            if rest[:2] == ["pkg", "get"]:
                if doc is None:
                    answer(1, "{}\n")
                answer(0, json.dumps(doc.get(rest[2]) if len(rest) > 2 else doc) + "\n")
            if rest[:2] == ["run", "build"]:
                if doc is None or todo.get("do") == "fail" or "build" not in (doc.get("scripts") or {}):
                    answer(1, "the build failed\n")
                outputs = doc.get("fake_build_output") or "build/out"
                outputs = outputs if isinstance(outputs, list) else [outputs]
                if todo.get("stray"):
                    outputs = outputs + ["next-env.d.ts"]
                for rel in outputs:
                    out = os.path.join(folder, rel)
                    os.makedirs(os.path.dirname(out), exist_ok=True)
                    with open(out, "w") as fh:
                        fh.write("built\n")
                    with open(os.path.join(ROOT, "wrote.jsonl"), "a") as fh:
                        fh.write(json.dumps({"folder": folder, "rel": rel}) + "\n")
                answer(0, "built\n")
        record(False)
        answer(2, "")
    if TOOL == "uv":
        todo = record(True)
        if ARGV[:1] == ["init"]:
            scaffold("uv", todo)
            answer(0, "Initialized project\n")
        answer(2, "")
    if TOOL == "python3":
        todo = record(False)
        script = ARGV[-1] if ARGV else ""
        if todo.get("do") == "fail" or not os.path.isfile(script):
            answer(1, "")
        answer(0, "Hello from script!\n")
    if TOOL == "riseadapter":
        todo = record(False)
        opts = dict(zip(ARGV[1::2], ARGV[2::2]))
        work = opts.get("--work", "")
        if not os.path.isfile(os.path.join(work, "AGENTS.md")):
            answer(1, "{}")
        answer(0, json.dumps({"match": todo.get("match", "same")}))
    answer(2, "")


main()
