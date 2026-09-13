import { readdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const origin = "https://floridalearninghub.org";
const pages = readdirSync(root)
  .filter((name) => name.endsWith(".html"))
  .sort((a, b) => a === "index.html" ? -1 : b === "index.html" ? 1 : a.localeCompare(b));
const canonical = (name) => name === "index.html" ? origin + "/" : origin + "/" + name;
const xml = '<?xml version="1.0" encoding="UTF-8"?>\n' +
  '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n' +
  pages.map((name) => '  <url><loc>' + canonical(name) + '</loc></url>').join("\n") +
  '\n</urlset>\n';
writeFileSync(join(root, "sitemap.xml"), xml, "utf8");
console.log("Wrote sitemap.xml with " + pages.length + " pages.");
