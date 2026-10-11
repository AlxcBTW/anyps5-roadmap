// The fixture build of the Python generator (tests/fixtures -> roadmap.py --offline), so these tests
// read the same shape the live site publishes. CONTRIBUTING.md has the command that regenerates it.
import type { RoadmapDoc } from "../data/schema";
import raw from "./fixture-roadmap.json";

export const fixture = raw as unknown as RoadmapDoc;
