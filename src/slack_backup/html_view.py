from __future__ import annotations

import json
from typing import Sequence


def render_html(records: Sequence[dict], manifest: dict) -> str:
    payload = json.dumps(
        {"records": records, "manifest": manifest},
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("<", "\\u003c")
    return _template().replace("__ARCHIVE_PAYLOAD__", payload)


def _template() -> str:
    return """<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Slack 발주 기록</title>
  <style>
    :root { color-scheme: light; --ink:#172033; --muted:#667085; --line:#d8deea; --panel:#fff; --soft:#f3f6fb; --accent:#3157a4; --accent-soft:#eaf0ff; --reply:#f7f9fc; }
    * { box-sizing:border-box; }
    body { margin:0; background:var(--soft); color:var(--ink); font:16px/1.55 Arial,"Apple SD Gothic Neo","Noto Sans KR",sans-serif; }
    header { position:sticky; top:0; z-index:10; background:rgba(255,255,255,.96); border-bottom:1px solid var(--line); backdrop-filter:blur(10px); }
    .topbar { max-width:1180px; margin:auto; padding:18px 24px 14px; }
    h1 { margin:0; font-size:1.35rem; letter-spacing:-.02em; }
    .summary { margin-top:4px; color:var(--muted); font-size:.88rem; }
    .controls { display:grid; grid-template-columns:minmax(220px,2fr) repeat(3,minmax(140px,1fr)); gap:10px; margin-top:14px; }
    input,select { width:100%; min-height:42px; border:1px solid #bfc8d8; border-radius:8px; background:#fff; color:var(--ink); padding:8px 10px; font:inherit; }
    main { max-width:1180px; margin:0 auto; padding:24px; }
    .date-section { margin:0 0 30px; }
    .date-heading { display:flex; align-items:center; gap:12px; margin:0 0 12px; font-size:1.05rem; }
    .date-heading::after { content:""; flex:1; height:1px; background:var(--line); }
    .message { display:grid; grid-template-columns:88px minmax(0,1fr); gap:14px; margin-bottom:10px; padding:16px; background:var(--panel); border:1px solid var(--line); border-radius:10px; box-shadow:0 1px 2px rgba(16,24,40,.04); }
    .message.reply { margin-left:44px; background:var(--reply); border-left:3px solid #9eb0d2; }
    .time { color:var(--muted); font-size:.84rem; font-variant-numeric:tabular-nums; }
    .meta { display:flex; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:5px; }
    .author { font-weight:700; }
    .badge { padding:2px 8px; border-radius:999px; background:var(--accent-soft); color:#244785; font-size:.76rem; font-weight:700; }
    .thread { color:var(--muted); font-size:.8rem; }
    .text { white-space:pre-wrap; overflow-wrap:anywhere; }
    .images { display:grid; grid-template-columns:repeat(auto-fit,minmax(220px,1fr)); gap:10px; margin-top:12px; }
    .image-link { display:flex; min-height:120px; align-items:center; justify-content:center; overflow:hidden; border:1px solid var(--line); border-radius:8px; background:#eef1f6; }
    .image-link img { display:block; max-width:100%; max-height:360px; object-fit:contain; }
    .file-error { margin-top:10px; padding:8px 10px; border-radius:6px; background:#fff1f0; color:#9f2d27; font-size:.85rem; }
    .missing { color:#9f2d27; font-size:.82rem; font-weight:700; }
    .empty { padding:54px 20px; text-align:center; color:var(--muted); }
    @media (max-width:760px) { .controls{grid-template-columns:1fr 1fr}.controls input{grid-column:1/-1}.message{grid-template-columns:1fr;gap:4px}.message.reply{margin-left:16px}.topbar,main{padding-left:16px;padding-right:16px} }
  </style>
</head>
<body>
  <header><div class="topbar">
    <h1>Slack 발주 기록</h1>
    <div class="summary" id="summary"></div>
    <div class="controls" aria-label="기록 필터">
      <input id="search" type="search" placeholder="메시지 또는 작성자 검색" aria-label="메시지 또는 작성자 검색">
      <select id="category" aria-label="메시지 종류"><option value="">모든 종류</option></select>
      <select id="author" aria-label="작성자"><option value="">모든 작성자</option></select>
      <input id="date" type="date" aria-label="날짜">
    </div>
  </div></header>
  <main id="archive"></main>
  <script>
    const archive = __ARCHIVE_PAYLOAD__;
    const controls = { search: document.querySelector('#search'), category: document.querySelector('#category'), author: document.querySelector('#author'), date: document.querySelector('#date') };
    const root = document.querySelector('#archive');
    const unique = key => [...new Set(archive.records.map(item => item[key]))].sort((a,b) => a.localeCompare(b,'ko'));
    const addOptions = (element, values) => values.forEach(value => { const option=document.createElement('option'); option.value=value; option.textContent=value; element.append(option); });
    addOptions(controls.category, unique('category')); addOptions(controls.author, unique('author'));
    const period=archive.manifest.dateRange; document.querySelector('#summary').textContent = `${period.start ?? '-'} ~ ${period.end ?? '-'} · 메시지 ${archive.records.length.toLocaleString('ko-KR')}개`;
    const el = (tag, className, text) => { const node=document.createElement(tag); if(className) node.className=className; if(text!==undefined) node.textContent=text; return node; };
    function render() {
      const query=controls.search.value.trim().toLocaleLowerCase('ko');
      const filtered=archive.records.filter(item => (!query || `${item.text} ${item.author}`.toLocaleLowerCase('ko').includes(query)) && (!controls.category.value || item.category===controls.category.value) && (!controls.author.value || item.author===controls.author.value) && (!controls.date.value || item.date===controls.date.value));
      root.replaceChildren();
      if(!filtered.length){ root.append(el('div','empty','조건에 맞는 기록이 없습니다.')); return; }
      const groups=Map.groupBy ? Map.groupBy(filtered,item=>item.date) : filtered.reduce((map,item)=>(map.set(item.date,[...(map.get(item.date)||[]),item]),map),new Map());
      for(const [date,items] of groups){ const section=el('section','date-section'); section.append(el('h2','date-heading',`${date} · ${items.length}개`)); for(const item of items) section.append(messageCard(item)); root.append(section); }
    }
    function messageCard(item){
      const card=el('article',`message${item.isThreadReply?' reply':''}`); card.id=item.id.replaceAll(':','-').replaceAll('.','-');
      card.append(el('div','time',item.time)); const body=el('div'); const meta=el('div','meta'); meta.append(el('span','author',item.author),el('span','badge',item.category));
      if(item.isThreadReply) meta.append(el('span','thread','스레드 답글'));
      if(item.threadParentMissing) meta.append(el('span','missing','원문이 선택 범위에 없음'));
      body.append(meta,el('div','text',item.text || '(텍스트 없음)'));
      const available=item.attachments.filter(file=>file.path); if(available.length){ const gallery=el('div','images'); for(const file of available){ const link=el('a','image-link'); link.href=file.path; link.target='_blank'; link.rel='noopener'; const image=el('img'); image.src=file.path; image.alt=file.name; image.loading='lazy'; link.append(image); gallery.append(link); } body.append(gallery); }
      for(const file of item.attachments.filter(file=>file.error)) body.append(el('div','file-error',`${file.name}: ${file.error}`));
      card.append(body); return card;
    }
    Object.values(controls).forEach(control=>control.addEventListener('input',render)); render();
  </script>
</body>
</html>"""

