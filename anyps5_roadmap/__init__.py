"""AnyPS5 blocker map generator.

Pipeline, in module order:

    collect   -> GitHub issues and PRs into the raw cache (gh api graphql)
    mine      -> text rules: title IDs, names, stages, error signatures, references
    model     -> mined + curated facts: titles, blockers, chains, ranking
    coverage  -> HLE / ISA (progress.json) and PM4 coverage
    assemble  -> roadmap.json
    render_md -> ROADMAP.md and llms.txt (classic.html is render_html.py at the repo root;
                 the front page is the web app in web/)
    cli       -> the command line (roadmap.py calls cli.main)
"""
