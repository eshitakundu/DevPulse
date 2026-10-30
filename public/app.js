// All comment text is untrusted, so everything is inserted with textContent, never innerHTML.
const $ = (id) => document.getElementById(id);
const el = (tag, text, cls) => {
  const node = document.createElement(tag);
  if (text) node.textContent = text;
  if (cls) node.className = cls;
  return node;
};

function renderPoints(list, points, comments) {
  list.replaceChildren();
  if (!points.length) return list.append(el("li", "None found.", "muted"));
  const byRef = Object.fromEntries(comments.map((c) => [c.ref, c]));
  for (const point of points) {
    const item = el("li");
    // The rule-based analyst uses the quote itself as the point; don't show it twice.
    const sameAsQuote = point.point.replace(/\.\.\.$/, "") === point.quote.slice(0, point.point.length - 3) ||
      point.point === point.quote;
    if (!sameAsQuote) item.append(el("strong", point.point));
    const quote = el("blockquote", `"${point.quote}"`);
    const sources = el("span", "", "sources");
    point.cites.filter((ref) => byRef[ref]).forEach((ref, i) => {
      const link = el("a", `${byRef[ref].author} on HN`);
      link.href = `https://news.ycombinator.com/item?id=${encodeURIComponent(byRef[ref].hn_id)}`;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      if (i) sources.append(", ");
      sources.append(link);
    });
    quote.append(" ", sources);
    item.append(quote);
    list.append(item);
  }
}

async function check(tool) {
  $("status").textContent = `Reading Hacker News threads about ${tool}…`;
  $("report").classList.add("hidden");
  try {
    const response = await fetch(`/api/report?tool=${encodeURIComponent(tool)}`);
    const body = await response.json();
    if (!response.ok) throw new Error(body.detail?.[0]?.msg || body.detail || "Something went wrong.");
    const { report, cached } = body;
    if (!report.comments.length) {
      $("status").textContent = `No Hacker News threads with "${tool}" in the title. Try the exact name.`;
      return;
    }
    $("status").textContent = "";
    const writer = report.written_by === "llm" ? "Written by a model, checked by the validator" : "Written by the rule-based analyst";
    $("summary").textContent =
      `${report.comments.length} comments from ${report.stories.length} threads: ${report.stories.join(" · ")}. ${writer}${cached ? " (cached today)" : ""}.`;
    renderPoints($("pros"), report.pros, report.comments);
    renderPoints($("cons"), report.cons, report.comments);
    $("trace").replaceChildren(...report.trace.map((step) => el("li", step)));
    $("rejected").replaceChildren(...report.rejected.map((r) => el("li", `${r.side}: ${r.point} (${r.reason})`)));
    $("rejected-block").classList.toggle("hidden", !report.rejected.length);
    $("report").classList.remove("hidden");
  } catch (error) {
    $("status").textContent = error.message;
  }
}

$("search").addEventListener("submit", (event) => {
  event.preventDefault();
  const tool = $("tool").value.trim();
  if (!tool) return;
  history.replaceState(null, "", `?tool=${encodeURIComponent(tool)}`);
  check(tool);
});

const initial = new URLSearchParams(location.search).get("tool");
if (initial) {
  $("tool").value = initial;
  check(initial);
}
