/* 設定の画面（/setup）。v0.3.0 から PIN の変更だけ（2026-11-20 作者の決定）。
 * 画面の差し替えとファーム更新モードは、本体ボタンを 3 秒押してから 10 分の間だけ使える。
 * ネットワーク・Art-Net・sACN・名前・許可リストは画面から外した（値はそのまま。POST /api/settings では今も変えられる）。 */
#ifndef SETUP_PAGE_H
#define SETUP_PAGE_H
#define SETUP_PAGE \
"<!doctype html><html lang=ja><meta charset=utf-8><meta name=viewport content='width=device-width'>" \
"<title>ODE 設定</title><style>body{font:16px system-ui;margin:16px;max-width:560px}label{display:block;margin:10px 0}" \
"input{font:inherit;width:100%;box-sizing:border-box;padding:6px}" \
"button{font:inherit;padding:8px 16px;margin:12px 8px 0 0}fieldset{margin:16px 0;border:1px solid #aaa;border-radius:8px}" \
"small{color:#666}.m{margin-top:8px;font-weight:bold}.ok{color:#0645ad}</style>" \
"<h1>ODE 設定</h1><p id=info></p>" \
"<form id=f><fieldset><legend>PIN の変更</legend>" \
"<label>いまの PIN<input id=pin type=password autocomplete=current-password></label>" \
"<label>新しい PIN（15 文字まで）<input id=newpin maxlength=15 autocomplete=new-password></label>" \
"<button>保存</button><p class=m id=m></p></fieldset></form>" \
"<fieldset><legend>画面の差し替え</legend><p id=win></p><p id=uiinfo></p>" \
"<label>miseru の <code>npm run build:box</code> で作った dist/box フォルダを選ぶ（index.html と assets/）<input type=file id=dir webkitdirectory multiple></label>" \
"<button id=up>アップロード</button><button id=reset>内蔵の画面に戻す</button><p class=m id=um></p></fieldset>" \
"<fieldset><legend>ファームの更新</legend><p>押すと LAN と DMX の出力が止まり、USB-C（J1）から書き込める状態（USB DFU）になります。Mac と USB-C でつなぎ、STM32CubeProgrammer の USB で書き込んでください。元に戻すには電源を入れ直します。本体ボタンを 3 秒押してから 10 分の間だけ使えます。</p>" \
"<label>いまの PIN<input id=dpin type=password></label>" \
"<button id=dfu>ファーム更新モードにする</button><p class=m id=dm></p></fieldset><script>" \
"const $=i=>document.getElementById(i),f=$('f');let ui_max=393200;" \
"const NB='いまは受け付けていません。本体のボタンを 3 秒押し続けて（LED が 3 回点滅）から、10 分以内にこの画面のボタンをもう一度押してください。';" \
"function msg(id,t,ok){const e=$(id);e.textContent=t;e.className='m'+(ok?' ok':'')}" \
"function load(){fetch('/api/settings').then(r=>r.json()).then(s=>{ui_max=s.ui_max;" \
"$('info').textContent='MAC '+s.mac+' / IP '+s.ip+' / 版 '+s.version+' / 同時接続の上限 '+s.max_clients;" \
"$('win').textContent=s.ui_open>0?'差し替えを受け付けています（あと '+Math.ceil(s.ui_open/60)+' 分）':'本体のボタンを 3 秒押し続けると（LED が 3 回点滅）、10 分間だけ差し替えられます。長押しでは照明は消えません。短く押して離すと今までどおりロック解除と全消灯です。';" \
"$('uiinfo').textContent=(s.ui=='uploaded'?'いまは差し替えた画面（'+Math.round(s.ui_size/1024)+'KB）':'いまは内蔵の画面')+'、上限 '+Math.round(s.ui_max/1024)+'KB';})}load();setInterval(load,15000);" \
"f.onsubmit=e=>{e.preventDefault();if(!$('newpin').value){msg('m','新しい PIN を入れてください');return}const d=new URLSearchParams();" \
"d.set('pin',$('pin').value);d.set('newpin',$('newpin').value);" \
"fetch('/api/settings',{method:'POST',body:d}).then(r=>r.json()).then(j=>{" \
"if(j.ok)msg('m',j.reboot?'保存しました。再起動します。少し待ってから開き直してください。':'保存しました。',1);else msg('m',j.error=='pin'?'PIN が違います':'値が正しくありません')})};" \
"async function gz(b){if(!window.CompressionStream)return null;return new Uint8Array(await new Response(new Blob([b]).stream().pipeThrough(new CompressionStream('gzip'))).arrayBuffer())}" \
"const MIME={html:'text/html; charset=utf-8',js:'application/javascript',css:'text/css',svg:'image/svg+xml',json:'application/json',png:'image/png',ico:'image/x-icon',woff2:'font/woff2',webmanifest:'application/manifest+json'};" \
"$('up').onclick=async()=>{const fs=[...$('dir').files];if(!fs.length){$('um').textContent='フォルダを選んでください';return}" \
"const parts=[],te=new TextEncoder();let names=[];for(const x of fs){let p=(x.webkitRelativePath||x.name).split('/');if(p.length>1)p=p.slice(1);p=p.join('/');" \
"if(p.startsWith('.')||p.includes('/.'))continue;names.push(p);const raw=new Uint8Array(await x.arrayBuffer());const z=await gz(raw);const use=z&&z.length<raw.length;const data=use?z:raw;" \
"const pb=te.encode(p),mb=te.encode(MIME[p.split('.').pop()]||'application/octet-stream');const h=new Uint8Array(1+pb.length+1+mb.length+5);let i=0;" \
"h[i++]=pb.length;h.set(pb,i);i+=pb.length;h[i++]=mb.length;h.set(mb,i);i+=mb.length;h[i++]=use?1:0;new DataView(h.buffer).setUint32(i,data.length,true);parts.push(h,data)}" \
"if(!names.includes('index.html')){$('um').textContent='index.html がありません（dist/box フォルダを選んでください）';return}" \
"const blob=new Blob(parts);if(blob.size>ui_max){$('um').textContent='大きすぎます（'+Math.round(blob.size/1024)+'KB、上限 '+Math.round(ui_max/1024)+'KB）';return}" \
"$('um').textContent='書き込み中…（'+Math.round(blob.size/1024)+'KB）';" \
"const r=await fetch('/api/ui',{method:'POST',body:blob}).then(r=>r.json()).catch(()=>({ok:false,error:'net'}));" \
"$('um').textContent=r.ok?'差し替えました。画面を開き直してください。':({button:NB,size:'大きすぎます',bundle:'中身が読めませんでした'}[r.error]||'失敗しました');load()};" \
"$('reset').onclick=async()=>{const r=await fetch('/api/ui/reset',{method:'POST'}).then(r=>r.json()).catch(()=>({ok:false}));" \
"$('um').textContent=r.ok?'内蔵の画面に戻しました。':(r.error=='button'?NB:'失敗しました');load()};" \
"$('dfu').onclick=async()=>{if(!confirm('ファーム更新モードにします。LAN と DMX の出力が止まります。よろしいですか？'))return;" \
"const r=await fetch('/api/dfu?pin='+encodeURIComponent($('dpin').value),{method:'POST'}).then(r=>r.json()).catch(()=>({ok:false}));" \
"$('dm').textContent=r.ok?'ファーム更新モードに入りました。USB-C で Mac とつないで書き込んでください（この画面はもう使えません）。':({pin:'PIN が違います',button:NB}[r.error]||'失敗しました')};" \
"</script></html>"
#endif
