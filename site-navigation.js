document.documentElement.classList.add("nav-enhanced");
document.addEventListener("DOMContentLoaded", function () {
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.getElementById("primary-nav");
  if (toggle && nav) {
    const close = function () {
      nav.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
    };
    toggle.addEventListener("click", function () {
      const open = !nav.classList.contains("is-open");
      nav.classList.toggle("is-open", open);
      toggle.setAttribute("aria-expanded", String(open));
    });
    nav.addEventListener("click", function (event) {
      if (event.target.closest("a")) close();
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") close();
    });
  }
  const parts = location.pathname.split("/").filter(Boolean);
  const segment = parts.length ? decodeURIComponent(parts[parts.length - 1]) : "";
  const file = !segment ? "index.html" : (segment.endsWith(".html") ? segment : segment + ".html");
  const topPages = new Set(["index.html","read-florida.html","discover-pioneer-florida.html","teach-pioneer-florida.html","classroom-resources.html","stories-and-books.html","today-in-florida-history.html"]);
  if (topPages.has(file)) return;
  const main = document.querySelector("main");
  const heading = main && main.querySelector("h1");
  const active = document.querySelector('#primary-nav a[aria-current="page"]');
  if (!main || !heading || !active) return;
  const crumb = document.createElement("nav");
  crumb.className = "breadcrumb";
  crumb.setAttribute("aria-label", "Breadcrumb");
  const home = document.createElement("a");
  home.href = "index.html";
  home.textContent = "Home";
  const section = active.cloneNode(true);
  section.removeAttribute("aria-current");
  const sep1 = document.createElement("span");
  const sep2 = document.createElement("span");
  const current = document.createElement("span");
  sep1.className = sep2.className = "breadcrumb-separator";
  sep1.textContent = sep2.textContent = "›";
  current.textContent = heading.textContent.trim();
  current.setAttribute("aria-current", "page");
  crumb.append(home, sep1, section, sep2, current);
  main.before(crumb);
});