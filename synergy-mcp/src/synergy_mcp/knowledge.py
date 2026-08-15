"""Knowledge corpus harvest, ingest, index and search helpers."""

from __future__ import annotations

import csv
import hashlib
import html
import os
import re
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

from .policy import READ_ONLY_COMMANDS

ALLOWED_CORPORA = frozenset({"cli", "manual", "query", "release-notes"})
ALLOWED_TRUST = frozenset({"harvested", "reference"})
DEFAULT_FAMILY = "ccm72"

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_FTS_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
_WHITESPACE_RE = re.compile(r"[ \t\r\f\v]+")


class KnowledgeError(RuntimeError):
    """Raised when the knowledge corpus cannot be harvested, built or searched."""


class _HtmlTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._skip_depth = 0
        self._heading_level: int | None = None
        self._lines: list[str] = []
        self._current: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self._flush()
            self._heading_level = int(tag[1])
        elif tag in {"p", "div", "section", "article", "li", "tr", "pre", "br"}:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self._skip_depth:
            self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag in {
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "p",
            "div",
            "section",
            "article",
            "li",
            "tr",
            "pre",
        }:
            self._flush()
            self._heading_level = None

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        text = _WHITESPACE_RE.sub(" ", html.unescape(data)).strip()
        if text:
            self._current.append(text)

    def text(self) -> str:
        self._flush()
        return "\n\n".join(line for line in self._lines if line.strip())

    def _flush(self) -> None:
        if not self._current:
            return
        text = " ".join(self._current).strip()
        self._current = []
        if not text:
            return
        if self._heading_level:
            self._lines.append(f"{'#' * self._heading_level} {text}")
        else:
            self._lines.append(text)


@dataclass(frozen=True)
class Document:
    path: Path
    body: str
    meta: dict[str, str]
    sha256: str


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    corpus: str
    family: str
    title: str
    heading_path: str
    body: str


def corpus_root() -> Path:
    override = os.environ.get("SYNERGY_MCP_ROOT")
    if override:
        return Path(override).expanduser().resolve()
    return Path(__file__).resolve().parents[3] / "synergy-mcp-server"


def knowledge_index_path(root: Path | None = None) -> Path:
    return (root or corpus_root()) / "build" / "synergy-knowledge.sqlite"


def _today() -> str:
    return date.today().isoformat()


def _slug(value: str) -> str:
    slug = _SLUG_RE.sub("-", value.lower()).strip("-")
    return slug or "document"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fts_query(value: str) -> str:
    tokens = _FTS_TOKEN_RE.findall(value)
    if not tokens:
        raise KnowledgeError("Search query must contain at least one word or number")
    return " ".join(f'"{token}"' for token in tokens)


def _parse_frontmatter(text: str, path: Path) -> tuple[dict[str, str], str]:
    match = _FRONTMATTER_RE.match(text)
    if not match:
        raise KnowledgeError(f"{path} is missing YAML frontmatter")

    meta: dict[str, str] = {}
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            raise KnowledgeError(f"Invalid frontmatter line in {path}: {line!r}")
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"').strip("'")

    body = text[match.end() :]
    _validate_meta(meta, path)
    return meta, body


def _validate_meta(meta: dict[str, str], path: Path) -> None:
    required = {
        "corpus",
        "doc_id",
        "title",
        "family",
        "source",
        "source_version",
        "harvested",
        "trust",
    }
    missing = sorted(required - meta.keys())
    if missing:
        raise KnowledgeError(f"{path} frontmatter is missing: {', '.join(missing)}")
    if meta["corpus"] not in ALLOWED_CORPORA:
        raise KnowledgeError(f"{path} has unknown corpus {meta['corpus']!r}")
    if meta["trust"] not in ALLOWED_TRUST:
        raise KnowledgeError(f"{path} has unknown trust {meta['trust']!r}")


def _frontmatter(meta: dict[str, str]) -> str:
    lines = ["---"]
    for key in (
        "corpus",
        "doc_id",
        "title",
        "family",
        "source",
        "source_version",
        "harvested",
        "trust",
    ):
        lines.append(f'{key}: "{meta[key]}"')
    lines.append("---")
    return "\n".join(lines) + "\n\n"


def _write_markdown(path: Path, meta: dict[str, str], body: str) -> Document:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _frontmatter(meta) + body.strip() + "\n"
    path.write_text(text, encoding="utf-8")
    return Document(path=path, body=body.strip(), meta=meta, sha256=_sha256(text))


def _read_document(path: Path) -> Document:
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text, path)
    return Document(path=path, body=body, meta=meta, sha256=_sha256(text))


def _manual_body(path: Path) -> str:
    raw = path.read_text(encoding="utf-8")
    if path.suffix.lower() not in {".html", ".htm"}:
        return raw
    parser = _HtmlTextExtractor()
    parser.feed(raw)
    text = parser.text()
    if not text:
        raise KnowledgeError(f"No extractable text found in HTML manual source: {path}")
    return text


def _write_manifest(directory: Path, documents: list[Document]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    manifest = directory / "manifest.csv"
    with manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "doc_id",
                "corpus",
                "title",
                "path",
                "family",
                "source_version",
                "sha256",
                "chunks",
                "ingested",
            ],
        )
        writer.writeheader()
        for doc in sorted(documents, key=lambda item: item.meta["doc_id"]):
            writer.writerow(
                {
                    "doc_id": doc.meta["doc_id"],
                    "corpus": doc.meta["corpus"],
                    "title": doc.meta["title"],
                    "path": doc.path.relative_to(directory).as_posix(),
                    "family": doc.meta["family"],
                    "source_version": doc.meta["source_version"],
                    "sha256": doc.sha256,
                    "chunks": len(chunk_document(doc)),
                    "ingested": _today(),
                }
            )


def harvest_ccm_help(
    *,
    database: str = "local",
    ccm_binary: str = "ccm",
    verbs: list[str] | None = None,
    source_version: str | None = None,
    root: Path | None = None,
) -> list[Document]:
    """Harvest `ccm help` and `ccm help <verb>` into markdown documents."""
    selected_verbs = verbs or sorted(READ_ONLY_COMMANDS)
    destination = (root or corpus_root()) / "cli-harvest" / _slug(database)

    if source_version is None:
        source_version = _run_ccm_text(ccm_binary, ["version"]).splitlines()[0].strip()

    documents = [
        _write_help_document(
            destination,
            title="ccm help",
            command=["help"],
            output=_run_ccm_text(ccm_binary, ["help"]),
            source_version=source_version,
        )
    ]

    for verb in selected_verbs:
        documents.append(
            _write_help_document(
                destination,
                title=f"ccm help {verb}",
                command=["help", verb],
                output=_run_ccm_text(ccm_binary, ["help", verb]),
                source_version=source_version,
            )
        )

    _write_manifest(destination, documents)
    return documents


def _run_ccm_text(ccm_binary: str, args: list[str]) -> str:
    try:
        result = subprocess.run(
            [ccm_binary, *args],
            check=True,
            shell=False,
            text=True,
            capture_output=True,
            timeout=120,
        )
    except FileNotFoundError as exc:
        raise KnowledgeError(f"ccm binary {ccm_binary!r} was not found") from exc
    except subprocess.CalledProcessError as exc:
        output = (exc.stdout or "") + (exc.stderr or "")
        raise KnowledgeError(f"ccm {' '.join(args)} failed: {output.strip()[:500]}") from exc
    return result.stdout.strip() or result.stderr.strip()


def _write_help_document(
    destination: Path,
    *,
    title: str,
    command: list[str],
    output: str,
    source_version: str,
) -> Document:
    source = "ccm " + " ".join(command)
    doc_id = _slug(source)
    meta = {
        "corpus": "cli",
        "doc_id": doc_id,
        "title": title,
        "family": DEFAULT_FAMILY,
        "source": source,
        "source_version": source_version,
        "harvested": _today(),
        "trust": "harvested",
    }
    body = f"# {title}\n\n```text\n{output.strip()}\n```"
    return _write_markdown(destination / f"{doc_id}.md", meta, body)


def ingest_manual_markdown(
    source: Path,
    *,
    doc_id: str | None = None,
    title: str | None = None,
    corpus: str = "manual",
    family: str = DEFAULT_FAMILY,
    source_version: str = "unknown",
    root: Path | None = None,
) -> list[Document]:
    """Ingest extracted manual markdown/text files into the corpus layout."""
    if corpus not in ALLOWED_CORPORA - {"cli"}:
        raise KnowledgeError(f"Manual ingest cannot write corpus {corpus!r}")
    source = source.expanduser().resolve()
    if not source.exists():
        raise KnowledgeError(f"Manual source does not exist: {source}")

    files = [source] if source.is_file() else sorted(source.rglob("*"))
    text_files = [p for p in files if p.suffix.lower() in {".md", ".txt", ".html", ".htm"}]
    pdf_files = [p for p in files if p.suffix.lower() == ".pdf"]
    if pdf_files and not text_files:
        raise KnowledgeError(
            "PDF manuals must be extracted to markdown or text before ingest; source PDFs are not indexed."
        )
    if not text_files:
        raise KnowledgeError(f"No markdown, text or HTML files found under {source}")

    base_doc_id = _slug(doc_id or source.stem or source.name)
    base_title = title or source.stem.replace("-", " ").replace("_", " ").title()
    destination = (root or corpus_root()) / ("release-notes" if corpus == "release-notes" else "manuals") / base_doc_id
    if destination.exists():
        for stale in destination.glob("*.md"):
            stale.unlink()
    documents: list[Document] = []

    for index, path in enumerate(text_files, start=1):
        raw = _manual_body(path)
        match = _FRONTMATTER_RE.match(raw)
        if match:
            meta, body = _parse_frontmatter(raw, path)
            target_name = f"{meta['doc_id']}.md"
        else:
            chapter_id = _slug(path.stem)
            suffix = chapter_id if len(text_files) > 1 else base_doc_id
            meta = {
                "corpus": corpus,
                "doc_id": suffix if suffix.startswith(base_doc_id) else f"{base_doc_id}-{suffix}",
                "title": base_title if len(text_files) == 1 else f"{base_title}: {path.stem}",
                "family": family,
                "source": str(path),
                "source_version": source_version,
                "harvested": _today(),
                "trust": "reference",
            }
            body = raw
            target_name = f"{index:03d}-{chapter_id}.md"
        documents.append(_write_markdown(destination / target_name, meta, body))

    _write_manifest(destination, documents)
    return documents


def load_documents(root: Path | None = None) -> list[Document]:
    base = root or corpus_root()
    documents: list[Document] = []
    for relative in ("cli-harvest", "manuals", "release-notes"):
        directory = base / relative
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*.md")):
            documents.append(_read_document(path))
    return documents


def chunk_document(document: Document) -> list[Chunk]:
    chunks: list[Chunk] = []
    heading_stack: list[tuple[int, str]] = []
    current_lines: list[str] = []
    current_path = document.meta["title"]

    def flush() -> None:
        body = "\n".join(current_lines).strip()
        if not body:
            return
        chunks.append(
            Chunk(
                doc_id=document.meta["doc_id"],
                corpus=document.meta["corpus"],
                family=document.meta["family"],
                title=document.meta["title"],
                heading_path=current_path,
                body=body,
            )
        )

    for line in document.body.splitlines():
        match = _HEADING_RE.match(line)
        if match and current_lines:
            flush()
            current_lines = []
        if match:
            level = len(match.group(1))
            text = match.group(2).strip()
            heading_stack = [(lvl, val) for lvl, val in heading_stack if lvl < level]
            heading_stack.append((level, text))
            current_path = " > ".join(value for _, value in heading_stack)
        current_lines.append(line)
    flush()

    return chunks


def build_knowledge_index(root: Path | None = None, index_path: Path | None = None) -> dict:
    base = root or corpus_root()
    index = index_path or knowledge_index_path(base)
    documents = load_documents(base)
    if not documents:
        raise KnowledgeError(
            f"No corpus markdown found under {base}. Run harvest-cli or ingest-manual first."
        )

    index.parent.mkdir(parents=True, exist_ok=True)
    if index.exists():
        index.unlink()

    with sqlite3.connect(index) as conn:
        conn.execute(
            "CREATE VIRTUAL TABLE chunks USING fts5("
            "doc_id, corpus, family, title, heading_path, body, "
            "tokenize = 'porter unicode61')"
        )
        conn.execute(
            "CREATE TABLE documents ("
            "doc_id TEXT PRIMARY KEY, corpus TEXT, title TEXT, path TEXT, "
            "family TEXT, source TEXT, source_version TEXT, trust TEXT, "
            "sha256 TEXT, ingested TEXT)"
        )

        total_chunks = 0
        seen: set[tuple[str, str]] = set()
        for document in documents:
            key = (document.meta["corpus"], document.meta["doc_id"])
            if key in seen:
                raise KnowledgeError(f"Duplicate doc_id in corpus: {key[0]}/{key[1]}")
            seen.add(key)
            chunks = chunk_document(document)
            total_chunks += len(chunks)
            conn.execute(
                "INSERT INTO documents VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    document.meta["doc_id"],
                    document.meta["corpus"],
                    document.meta["title"],
                    document.path.relative_to(base).as_posix(),
                    document.meta["family"],
                    document.meta["source"],
                    document.meta["source_version"],
                    document.meta["trust"],
                    document.sha256,
                    _today(),
                ),
            )
            conn.executemany(
                "INSERT INTO chunks VALUES (?, ?, ?, ?, ?, ?)",
                [
                    (
                        chunk.doc_id,
                        chunk.corpus,
                        chunk.family,
                        chunk.title,
                        chunk.heading_path,
                        chunk.body,
                    )
                    for chunk in chunks
                ],
            )

    return {"index": str(index), "documents": len(documents), "chunks": total_chunks}


def search_knowledge(
    query: str,
    *,
    corpus: str | None = None,
    family: str | None = None,
    limit: int = 10,
    index_path: Path | None = None,
) -> dict:
    index = index_path or knowledge_index_path()
    if not index.exists():
        raise KnowledgeError(f"Knowledge index not found at {index}. Run `synergy-knowledge build`.")
    if corpus and corpus not in ALLOWED_CORPORA:
        raise KnowledgeError(f"Unknown corpus {corpus!r}")
    limit = max(1, min(limit, 50))

    filters = []
    params: list[str | int] = [_fts_query(query)]
    if corpus:
        filters.append("chunks.corpus = ?")
        params.append(corpus)
    if family:
        filters.append("chunks.family = ?")
        params.append(family)
    where = " AND ".join(["chunks MATCH ?", *filters])
    params.append(limit)

    sql = (
        "SELECT chunks.doc_id, chunks.corpus, chunks.family, chunks.title, "
        "chunks.heading_path, snippet(chunks, 5, '<mark>', '</mark>', '...', 32), "
        "documents.source, documents.source_version, documents.trust "
        "FROM chunks JOIN documents ON chunks.doc_id = documents.doc_id "
        f"WHERE {where} ORDER BY bm25(chunks) LIMIT ?"
    )

    with sqlite3.connect(index) as conn:
        rows = conn.execute(sql, params).fetchall()

    return {
        "query": query,
        "corpus": corpus,
        "family": family,
        "index": str(index),
        "results": [
            {
                "doc_id": row[0],
                "corpus": row[1],
                "family": row[2],
                "title": row[3],
                "heading_path": row[4],
                "snippet": row[5],
                "source": row[6],
                "source_version": row[7],
                "trust": row[8],
            }
            for row in rows
        ],
    }