// Small Markdown renderer for the assistant's answers (bold, italic, lists, separator), no injected HTML.

function esc(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function inline(s) {
  return esc(s)
    .replace(/\\\*/g, "&#42;")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/(^|[^*])\*([^*\s][^*]*?)\*(?!\*)/g, "$1<em>$2</em>")
    .replace(/\[(D\d{2,3}|M\d{2}|F\d{2}|I\d{2}|C\d{2})\]/g, '<span class="md-ref">$1</span>');
}

export function markdownToHtml(text) {
  const lines = String(text || "").replace(/\r/g, "").split("\n");
  const out = [];
  let list = null;
  const flush = () => {
    if (list) out.push(`<ul>${list.map((li) => `<li>${inline(li)}</li>`).join("")}</ul>`);
    list = null;
  };
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (/^\s*[-•]\s+/.test(line)) {
      (list = list || []).push(line.replace(/^\s*[-•]\s+/, ""));
      continue;
    }
    flush();
    if (!line.trim()) continue;
    if (/^-{3,}$/.test(line.trim())) out.push("<hr/>");
    else if (/^#{1,4}\s+/.test(line)) out.push(`<p><strong>${inline(line.replace(/^#{1,4}\s+/, ""))}</strong></p>`);
    else if (/^&gt;|^>/.test(line)) out.push(`<blockquote>${inline(line.replace(/^>\s?/, ""))}</blockquote>`);
    else out.push(`<p>${inline(line)}</p>`);
  }
  flush();
  return out.join("");
}
