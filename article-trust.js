document.addEventListener("DOMContentLoaded", function () {
  const file = location.pathname.split("/").pop() || "index.html";
  const excluded = new Set(["index.html","read-florida.html","discover-pioneer-florida.html","teach-pioneer-florida.html","classroom-resources.html","stories-and-books.html","today-in-florida-history.html","about-flh.html","about-author.html","research-standards.html","image-copyright-policy.html","corrections-policy.html","before-texas-book.html","florida-cracker-cattle-book.html"]);
  const main = document.querySelector("main");
  const article = main && main.querySelector(".article");
  if (!article || excluded.has(file)) return;
  const title = article.querySelector("h1");
  if (!title) return;
  const subtitle = article.querySelector(".subtitle");
  const kicker = article.querySelector(".kicker");
  const idMatch = (kicker && kicker.textContent.match(/FLH-\d{4}/)) || article.textContent.match(/FLH-\d{4}/) || [];
  const articleId = idMatch[0] || "";
  const sourceHeading = Array.from(article.querySelectorAll("h2,h3")).find(function (el) {
    return /^(sources|references|source notes)/i.test(el.textContent.trim());
  });
  if (sourceHeading) sourceHeading.id = "article-sources";
  const legacyByline = Array.from(article.children).find(function (el) {
    return el.tagName === "P" && /^By Wm\. E\. McMullen II$/i.test(el.textContent.trim());
  });
  if (legacyByline) legacyByline.remove();
  const trust = document.createElement("aside");
  trust.className = "article-trust";
  trust.setAttribute("aria-label", "Article authorship and editorial information");
  const label = document.createElement("div");
  label.className = "kicker";
  label.textContent = "Florida Learning Hub Editorial Information";
  const author = document.createElement("p");
  author.innerHTML = 'Researched and written by <a href="about-author.html"><strong>Wm. E. McMullen II</strong></a>';
  const details = document.createElement("p");
  details.className = "article-trust-details";
  if (articleId) {
    const idText = document.createElement("span");
    idText.textContent = "Article ID: " + articleId;
    details.append(idText);
  }
  if (sourceHeading) {
    const sourceLink = document.createElement("a");
    sourceLink.href = "#article-sources";
    sourceLink.textContent = "View sources";
    details.append(sourceLink);
  }
  const standards = document.createElement("a");
  standards.href = "research-standards.html";
  standards.textContent = "Research standards";
  details.append(standards);
  const corrections = document.createElement("a");
  corrections.href = "corrections-policy.html";
  corrections.textContent = "Corrections policy";
  details.append(corrections);
  trust.append(label, author, details);
  (subtitle || title).after(trust);
  const citation = document.createElement("section");
  citation.className = "suggested-citation";
  citation.setAttribute("aria-labelledby", "suggested-citation-heading");
  const citeHeading = document.createElement("h3");
  citeHeading.id = "suggested-citation-heading";
  citeHeading.textContent = "Suggested Citation";
  const accessDate = new Intl.DateTimeFormat("en-US", {month:"long", day:"numeric", year:"numeric"}).format(new Date());
  const pageUrl = location.href.split("#")[0].split("?")[0];
  const citationText = "McMullen, Wm. E., II. " + title.textContent.trim() + ". Florida Learning Hub" + (articleId ? ", " + articleId : "") + ". " + pageUrl + " (accessed " + accessDate + ").";
  const citeText = document.createElement("p");
  citeText.textContent = citationText;
  const copy = document.createElement("button");
  copy.type = "button";
  copy.className = "citation-copy";
  copy.textContent = "Copy citation";
  copy.addEventListener("click", async function () {
    try {
      await navigator.clipboard.writeText(citationText);
      copy.textContent = "Citation copied";
      setTimeout(function () { copy.textContent = "Copy citation"; }, 1800);
    } catch (error) {
      copy.textContent = "Select and copy the citation above";
    }
  });
  citation.append(citeHeading, citeText, copy);
  const cta = article.querySelector(".article-cta");
  if (cta) article.insertBefore(citation, cta);
  else article.append(citation);
});