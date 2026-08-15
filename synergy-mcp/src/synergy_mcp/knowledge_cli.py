"""Command line entry point for the local Synergy knowledge corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .knowledge import (
    KnowledgeError,
    build_knowledge_index,
    harvest_ccm_help,
    ingest_manual_markdown,
    search_knowledge,
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="synergy-knowledge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    harvest = subparsers.add_parser("harvest-cli", help="Harvest `ccm help` output")
    harvest.add_argument("--database", default="local", help="Corpus directory label")
    harvest.add_argument("--ccm-binary", default="ccm", help="Path to the ccm client")
    harvest.add_argument("--source-version", help="Override the captured ccm version string")
    harvest.add_argument("--verb", action="append", dest="verbs", help="Specific ccm verb to harvest")

    ingest = subparsers.add_parser("ingest-manual", help="Ingest extracted manual markdown/text")
    ingest.add_argument("source", type=Path, help="Markdown/text file or directory")
    ingest.add_argument("--doc-id", help="Stable document id prefix")
    ingest.add_argument("--title", help="Human-readable title")
    ingest.add_argument("--corpus", choices=["manual", "query", "release-notes"], default="manual")
    ingest.add_argument("--family", default="ccm72")
    ingest.add_argument("--source-version", default="unknown")

    subparsers.add_parser("build", help="Build the SQLite FTS5 search index")

    search = subparsers.add_parser("search", help="Search the built corpus")
    search.add_argument("query")
    search.add_argument("--corpus", choices=["cli", "manual", "query", "release-notes"])
    search.add_argument("--family")
    search.add_argument("--limit", type=int, default=10)

    args = parser.parse_args()

    try:
        if args.command == "harvest-cli":
            docs = harvest_ccm_help(
                database=args.database,
                ccm_binary=args.ccm_binary,
                verbs=args.verbs,
                source_version=args.source_version,
            )
            print(json.dumps({"harvested": len(docs)}, indent=2))
        elif args.command == "ingest-manual":
            docs = ingest_manual_markdown(
                args.source,
                doc_id=args.doc_id,
                title=args.title,
                corpus=args.corpus,
                family=args.family,
                source_version=args.source_version,
            )
            print(json.dumps({"ingested": len(docs)}, indent=2))
        elif args.command == "build":
            print(json.dumps(build_knowledge_index(), indent=2))
        elif args.command == "search":
            print(
                json.dumps(
                    search_knowledge(
                        args.query,
                        corpus=args.corpus,
                        family=args.family,
                        limit=args.limit,
                    ),
                    indent=2,
                )
            )
    except KnowledgeError as exc:
        parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
    main()