// A dependency-free static build from the Wagtail v2 API (chapter 7).
// Run: CMS_URL=http://localhost:8000 node frontend/build.mjs
// Astro, Next.js or Eleventy do the same three things: list pages, fetch each one, render its blocks.
import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

const CMS = process.env.CMS_URL ?? "http://localhost:8000";
const OUT = process.env.OUT_DIR ?? "frontend/dist";

async function api(path) {
  const response = await fetch(`${CMS}/api/v2/${path}`);
  if (!response.ok) throw new Error(`${response.status} for ${path}`);
  return response.json();
}

// Fetch every page of results: the API caps limit at WAGTAILAPI_LIMIT_MAX (20 by default).
async function allPages(query) {
  const items = [];
  for (let offset = 0; ; offset += 20) {
    const data = await api(`pages/?${query}&limit=20&offset=${offset}`);
    items.push(...data.items);
    if (items.length >= data.meta.total_count) return items;
  }
}

const escape = (text) =>
  String(text).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

// One renderer per block type. Unknown types render nothing, and say so, rather than crashing the build.
const renderers = {
  heading: (v) => `<${v.level} id="${escape(v.anchor || v.text.toLowerCase().replace(/\W+/g, "-"))}">${escape(v.text)}</${v.level}>`,
  paragraph: (v) => v, // rich text arrives as HTML; it was cleaned on the way in (chapter 6)
  code: (v) => `<pre class="lang-${escape(v.language)}"><code>${v.highlighted}</code></pre>`,
  note: (v) => `<aside class="note note-${escape(v.tone)}">${v.text}</aside>`,
  image: (v) =>
    `<figure><img src="${escape(v.src)}" width="${v.width}" height="${v.height}" alt="${escape(v.alt)}" loading="lazy">` +
    (v.caption ? `<figcaption>${escape(v.caption)}</figcaption>` : "") + `</figure>`,
};

function renderBody(blocks) {
  return blocks
    .map((block) => {
      const render = renderers[block.type];
      if (!render) console.warn(`No renderer for block type "${block.type}"`);
      return render ? render(block.value) : "";
    })
    .join("\n");
}

const layout = (title, content) =>
  `<!doctype html><html lang="en-GB"><head><meta charset="utf-8"><title>${escape(title)}</title></head><body>${content}</body></html>`;

const posts = await allPages("type=blog.BlogPage&fields=intro,date&order=-date");
const index = [];
for (const summary of posts) {
  const post = await api(`pages/${summary.id}/`);
  const slug = post.meta.slug;
  await mkdir(join(OUT, slug), { recursive: true });
  await writeFile(
    join(OUT, slug, "index.html"),
    layout(post.title, `<article><h1>${escape(post.title)}</h1><p>${escape(post.intro)}</p>${renderBody(post.body)}</article>`),
  );
  index.push(`<li><a href="/${slug}/">${escape(post.title)}</a> <time>${post.date}</time></li>`);
}
await writeFile(join(OUT, "index.html"), layout("Writing", `<ul>${index.join("")}</ul>`));
console.log(`Built ${posts.length} posts into ${OUT}`);
