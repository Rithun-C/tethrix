// Test file for .semgrep/rules/no-raw-html.yaml. Not part of the app.
// "ruleid:" marks a line the rule must flag. "ok:" marks a line it must leave alone.

export function Bad({ html }: { html: string }) {
  // ruleid: no-dangerously-set-inner-html
  return <div dangerouslySetInnerHTML={{ __html: html }} />;
}

export function BadWithOtherProps({ html }: { html: string }) {
  // ruleid: no-dangerously-set-inner-html
  return <p className="note" dangerouslySetInnerHTML={{ __html: html }}></p>;
}

export function badProps(html: string) {
  // ruleid: no-dangerously-set-inner-html
  return { className: "note", dangerouslySetInnerHTML: { __html: html } };
}

export function badDom(el: HTMLElement, html: string) {
  // ruleid: no-inner-html-assignment
  el.innerHTML = html;
  // ruleid: no-inner-html-assignment
  el.innerHTML += html;
  // ruleid: no-inner-html-assignment
  el.outerHTML = html;
  // ruleid: no-inner-html-assignment
  el.insertAdjacentHTML("beforeend", html);
}

export function Good({ text }: { text: string }) {
  // ok: no-dangerously-set-inner-html
  return <div className="note">{text}</div>;
}

export function goodDom(el: HTMLElement, text: string) {
  // ok: no-inner-html-assignment
  el.textContent = text;
  // ok: no-inner-html-assignment
  const current = el.innerHTML;
  return current.length;
}
