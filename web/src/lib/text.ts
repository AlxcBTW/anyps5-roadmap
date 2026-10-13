// Text matching for the search boxes: case and accents never decide a match.

/** Lower case without Latin accents, so "yotei" finds "Yōtei" and "pokemon" finds "Pokémon". */
export function fold(text: string): string {
  return text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

/**
 * The terms of a query: its words, and each "quoted part" as one term with its spaces. A row matches when it
 * holds every term, in any order, so an error line pasted in quotes still has to appear as written.
 */
export function searchTerms(q: string): string[] {
  const terms: string[] = [];
  for (const m of fold(q).matchAll(/"([^"]+)"|(\S+)/g)) {
    const term = (m[1] ?? m[2].replaceAll('"', "")).trim();
    if (term) terms.push(term);
  }
  return terms;
}

export function matchesTerms(haystack: string, terms: readonly string[]): boolean {
  return terms.every((t) => haystack.includes(t));
}
