# The front page is a client-side app over roadmap.json

The page used to be one static HTML file that render_html.py wrote with everything in it: every
blocker, every game and the coverage map, 570 KB at once. It was built to work without JavaScript,
and it read as a wall of text. We made the front page a React app in `web/`, built in CI and served
from GitHub Pages next to the files roadmap.py writes. It fetches `roadmap.json` and `feed.json` in the
browser, renders one view at a time, opens details on demand and loads the coverage map only when
someone opens it. Every blocker, game, filter and sort has a hash route, so links work on a static
host, and the classic page's anchors map onto them.

The Python generator stays the only producer of data, and the app reads nothing it does not publish,
so people, tools and agents still see the same facts. The cost is that the front page needs
JavaScript. The classic page stays as `classic.html` for that case, linked from the app's
`<noscript>`, and is still the front page of a build made without Node.

## Considered options

- **Keep server-rendered HTML and add more script.** Rejected: filters, sorting, a drawer per item and
  deep links over one prerendered file mean rebuilding an app by hand, and the file still ships
  everything at once.
- **Render the app at build time (static pages per blocker and game).** Rejected for now: hundreds of
  pages per hourly build for little gain, since the data changes every hour and the views are lists
  over one JSON file.
- **A table or UI library.** Rejected: the lists have under 200 rows and sort on one column at a time,
  and the design system already exists; a sort and filter module of a few dozen lines, tested, does
  the job. Runtime dependencies are `react` and `react-dom` only.
