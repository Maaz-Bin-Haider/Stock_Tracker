export interface PaginatedResponse<T> {
  results: T[];
  next: string | null;
}

function sameOriginPath(path: string): string {
  if (!/^https?:\/\//i.test(path)) return path;
  const url = new URL(path);
  return `${url.pathname}${url.search}${url.hash}`;
}

/**
 * Load every page of a DRF page-number-paginated endpoint.
 *
 * Choice controls must not silently stop at REST_FRAMEWORK.PAGE_SIZE. The
 * visited-URL guard also prevents a malformed API response from creating an
 * infinite request loop in the browser.
 */
export async function collectPaginated<T>(
  firstPath: string,
  loadPage: (path: string) => Promise<PaginatedResponse<T>>,
): Promise<T[]> {
  const rows: T[] = [];
  const visited = new Set<string>();
  let next: string | null = firstPath;

  while (next) {
    // DRF normally returns an absolute `next` URL. Convert it back to a
    // same-origin path so deployments on a non-default port keep that port,
    // and so choice loading can never follow a different origin.
    const pagePath = sameOriginPath(next);
    if (visited.has(pagePath)) {
      throw new Error(`Pagination loop detected at ${pagePath}`);
    }
    visited.add(pagePath);

    const page = await loadPage(pagePath);
    rows.push(...page.results);
    next = page.next;
  }

  return rows;
}
