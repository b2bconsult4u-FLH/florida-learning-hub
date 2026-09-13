document.documentElement.classList.add("nav-enhanced");
document.addEventListener("DOMContentLoaded",()=>{
  const toggle=document.querySelector(".nav-toggle"),nav=document.getElementById("primary-nav");
  if(toggle&&nav){
    const close=()=>{nav.classList.remove("is-open");toggle.setAttribute("aria-expanded","false")};
    toggle.addEventListener("click",()=>{const open=!nav.classList.contains("is-open");nav.classList.toggle("is-open",open);toggle.setAttribute("aria-expanded",String(open))});
    nav.addEventListener("click",event=>{if(event.target.closest("a"))close()});
    document.addEventListener("keydown",event=>{if(event.key==="Escape")close()});
  }
  const file=location.pathname.split("/").pop()||"index.html";
  const topPages=new Set(["index.html","read-florida.html","discover-pioneer-florida.html","teach-pioneer-florida.html","classroom-resources.html","stories-and-books.html","today-in-florida-history.html"]);
  const policyPages=new Set(["about-flh.html","about-author.html","research-standards.html","image-copyright-policy.html","corrections-policy.html"]);
  const bookPages=new Set(["before-texas-book.html","florida-cracker-cattle-book.html"]);
  const main=document.querySelector("main"),heading=main&&main.querySelector("h1"),active=document.querySelector('#primary-nav a[aria-current="page"]');
  if(!topPages.has(file)&&!policyPages.has(file)&&main&&heading&&active){
    const crumb=document.createElement("nav");crumb.className="breadcrumb";crumb.setAttribute("aria-label","Breadcrumb");
    const home=document.createElement("a");home.href="index.html";home.textContent="Home";
    const section=active.cloneNode(true);section.removeAttribute("aria-current");
    const sep1=document.createElement("span"),sep2=document.createElement("span"),current=document.createElement("span");
    sep1.className=sep2.className="breadcrumb-separator";sep1.textContent=sep2.textContent="›";
    current.textContent=heading.textContent.trim();current.setAttribute("aria-current","page");
    crumb.append(home,sep1,section,sep2,current);main.before(crumb);
  }
  const article=main&&main.querySelector(".article");
  if(!article||topPages.has(file)||policyPages.has(file)||bookPages.has(file))return;
  const title=article.querySelector("h1");
  if(!title)return;
  const subtitle=article.querySelector(".subtitle");
  const kicker=article.querySelector(".kicker");
  const id=((kicker&&kicker.textContent.match(/FLH-\d{4}/))||article.textContent.match(/FLH-\d{4}/)||[])[0]||"";
  const sourceHeading=[...article.querySelectorAll("h2,h3")].find(el=>/^(sources|references|source notes)/i.test(el.textContent.trim()));
  if(sourceHeading)sourceHeading.id="article-sources";
  const legacyByline=[...article.children].find(el=>el.tagName==="P"&&/^By Wm\. E\. McMullen II$/i.test(el.textContent.trim()));
  if(legacyByline)legacyByline.remove();
  const trust=document.createElement("aside");trust.className="article-trust";trust.setAttribute("aria-label","Article authorship and editorial information");
  const label=document.createElement("div");label.className="kicker";label.textContent="Florida Learning Hub Editorial Information";
  const author=document.createElement("p");author.innerHTML='Researched and written by <a href="about-author.html"><strong>Wm. E. McMullen II</strong></a>';
  const details=document.createElement("p");details.className="article-trust-details";
  if(id){const idText=document.createElement("span");idText.textContent="Article ID: "+id;details.append(idText);}
  if(sourceHeading){const sourceLink=document.createElement("a");sourceLink.href="#article-sources";sourceLink.textContent="View sources";details.append(sourceLink);}
  const standards=document.createElement("a");standards.href="research-standards.html";standards.textContent="Research standards";details.append(standards);
  const corrections=document.createElement("a");corrections.href="corrections-policy.html";corrections.textContent="Corrections policy";details.append(corrections);
  trust.append(label,author,details);
  (subtitle||title).after(trust);
  const citation=document.createElement("section");citation.className="suggested-citation";citation.setAttribute("aria-labelledby","suggested-citation-heading");
  const citeHeading=document.createElement("h3");citeHeading.id="suggested-citation-heading";citeHeading.textContent="Suggested Citation";
  const accessDate=new Intl.DateTimeFormat("en-US",{month:"long",day:"numeric",year:"numeric"}).format(new Date());
  const pageUrl=location.href.split("#")[0].split("?")[0];
  const citationText='McMullen, Wm. E., II. “‘+title.textContent.trim()+'.” Florida Learning Hub'+(id?", "+id:"")+". "+pageUrl+" (accessed "+accessDate+").";
  const citeText=document.createElement("p");citeText.textContent=citationText;
  const copy=document.createElement("button");copy.type="button";copy.className="citation-copy";copy.textContent="Copy citation";
  copy.addEventListener("click",async()=>{try{await navigator.clipboard.writeText(citationText);copy.textContent="Citation copied";setTimeout(()=>copy.textContent="Copy citation",1800)}catch{copy.textContent="Select and copy the citation above"}});
  citation.append(citeHeading,citeText,copy);
  const cta=article.querySelector(".article-cta");if(cta)article.insertBefore(citation,cta);else article.append(citation);
});