export interface SchemePlaybookEntry {
  id: string;
  name: string;
  tagline: string;
  description: string;
  bestFor: string;
  fit: string;
  nextStep: string;
}

export const schemePlaybook: SchemePlaybookEntry[] = [
  {
    id: "round-robin",
    name: "Round robin",
    tagline: "Everyone meets everyone once.",
    description: "League-style scheduling that produces rich standings, obvious cut lines, and a strong story for public tables and TV views.",
    bestFor: "Season play, club nights, smaller fields, and any event where fairness across the whole field matters more than fast elimination.",
    fit: "Now supported",
    nextStep: "Pair naturally with the new standings cut-line UI and a future Page playoff finish.",
  },
  {
    id: "swiss",
    name: "Swiss",
    tagline: "Fixed rounds, pair by current score.",
    description: "Scales better than round robin for larger fields because everybody keeps playing while opponents converge toward similar records.",
    bestFor: "Chess-like events, card games, board games, and medium-to-large competitions where you want fewer rounds without early elimination.",
    fit: "Now supported",
    nextStep: "Use it when you want fewer rounds than a league schedule while keeping everyone in contention until the fixed finish.",
  },
  {
    id: "page-playoff",
    name: "Page playoff",
    tagline: "Top four playoff with a double chance for seeds 1 and 2.",
    description: "A strong finals format after standings-based play because it rewards regular-season performance without going full double elimination.",
    bestFor: "Round-robin or league stages that should finish with a short playoff and a premium final.",
    fit: "Now supported",
    nextStep: "Currently ships as a seeded top-four finals format; the next step is wiring it directly after round-robin or Swiss standings stages.",
  },
  {
    id: "ladder",
    name: "Ladder",
    tagline: "Ongoing challenge-based ranking.",
    description: "Useful for communities and clubs where players climb over time instead of following a fixed round schedule.",
    bestFor: "Long-running club ecosystems, practice ladders, and flexible challenge formats.",
    fit: "Lower fit today",
    nextStep: "Would need challenge workflows, no fixed rounds, and a ranking-first product model.",
  },
  {
    id: "mcmahon",
    name: "McMahon",
    tagline: "Seeded Swiss with rating-aware starting points.",
    description: "A niche but smart option when you already trust pre-event ratings and want to avoid early mismatches even more aggressively than Swiss.",
    bestFor: "Go, chess, and rating-heavy communities that expect seeded Swiss-style pairing logic.",
    fit: "Specialist later addition",
    nextStep: "Makes most sense after a core Swiss engine exists.",
  },
];
