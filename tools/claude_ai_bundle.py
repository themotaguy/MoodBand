"""Bundle the project docs into one Markdown file for a claude.ai Project.

claude.ai Projects don't sync with this repo, so upload the bundle to the
Project's knowledge after docs change. The repo stays the source of truth.

Usage: python3 tools/claude_ai_bundle.py   ->  build/claude_ai_bundle.md
"""

from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "build" / "claude_ai_bundle.md"

# In reading order: entry point, then decisions, then supporting detail.
FILES = [
    ("CLAUDE.md", "Project overview and current status"),
    ("Docs/decisions.md", "Decision log (ADR-style) and open items"),
    ("Docs/feedback-module-plan.md", "Feedback-decision module design"),
    ("Docs/datasets.md", "Training datasets and access status"),
    ("Docs/proposal-summary.md", "Proposal summary and divergences"),
    ("Docs/haptics-prototype-test.md", "iPhone prototype test checklist and results"),
    ("README.md", "Repository README (results, structure, setup)"),
]


def main():
    parts = [
        "# MoodBand — project context bundle",
        "",
        f"Snapshot generated {date.today():%b %d, %Y} from the MoodBand repository "
        "(the repo is the source of truth; this is a copy for a claude.ai Project). "
        "The final literature review is a separate PDF "
        "(RitikMota_Capstone_LiteratureReview_mk5.pdf).",
        "",
        "Contents:",
        *[f"- `{path}` — {desc}" for path, desc in FILES],
    ]
    for path, desc in FILES:
        text = (ROOT / path).read_text().strip()
        parts += ["", "---", "", f"<!-- file: {path} — {desc} -->", "", text]
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text("\n".join(parts) + "\n")
    print(f"Wrote {OUT.relative_to(ROOT)} ({len(OUT.read_text().split()):,} words)")


if __name__ == "__main__":
    main()
