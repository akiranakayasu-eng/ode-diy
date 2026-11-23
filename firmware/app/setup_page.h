/* 設定の画面（/setup）。v0.3.1 で整理（2026-11-23 作者の依頼「もう少しわかりやすく、不要なものは外していい」）。
 * 上から: 画面の差し替え（SW2 の 3 秒長押しで 10 分だけ）、miseru の Admin の PIN、ファームの更新の説明（SW2 を 10 秒、画面のボタンは無い）。
 * ネットワーク・Art-Net・sACN・名前・許可リストは画面に出さない（値はそのまま。POST /api/settings では今も変えられる）。 */
#ifndef SETUP_PAGE_H
#define SETUP_PAGE_H
#define SETUP_PAGE \
"<!doctype html><html lang=ja><meta charset=utf-8><meta name=viewport content='width=device-width'>" \
"<title>ODE 設定</title><style>" \
"body{font:16px/1.6 system-ui;margin:0 auto;padding:16px;max-width:560px;color:#222;background:#f4f4f2}" \
"h1{font-size:22px;margin:0 0 4px}h2{font-size:17px;margin:0 0 8px}.sub{color:#666;font-size:14px;margin:0 0 16px}" \
"section{background:#fff;border:1px solid #ddd;border-radius:10px;padding:14px 16px;margin:0 0 14px}" \
"label{display:block;margin:8px 0;font-size:14px;color:#444}input[type=password],input[type=text]{font:inherit;width:100%;box-sizing:border-box;padding:7px;border:1px solid #bbb;border-radius:6px}" \
"button{font:inherit;padding:8px 18px;margin:10px 8px 0 0;border-radius:6px;border:1px solid #888;background:#fff;cursor:pointer}button.main{background:#0645ad;color:#fff;border-color:#0645ad}" \
"button:disabled{opacity:.45;cursor:default}.st{padding:8px 10px;border-radius:6px;font-weight:bold;margin:0 0 10px}" \
".open{background:#e3f4e3;color:#17631a}.closed{background:#eee;color:#555;font-weight:normal}.m{margin:8px 0 0;font-weight:bold;min-height:1em}.ok{color:#0645ad}.ng{color:#b00020}" \
".intro{background:#fff8e1;border-color:#e0c060}.intro ul{margin:8px 0;padding-left:20px}.warn{color:#b00020;font-weight:bold}.key{color:#8a4b00;font-weight:bold}.pinst{padding:6px 10px;border-radius:6px;font-weight:bold;margin:0 0 8px}.pdef{background:#fff1e0;color:#8a4b00}.pchg{background:#e3f4e3;color:#17631a}a{color:#0645ad}small{color:#777}details summary{cursor:pointer;font-weight:bold}</style>" \
"<h1>ODE 設定</h1><p class=sub id=info></p>" \
"<section class=intro><b>この画面の 3 つは、どれも本体の LOCK ボタン（SW2、<span class=warn>RESET ではない方</span>）を長押ししてからでないと動きません。</b>" \
"<ul><li>PIN の変更: SW2 を <b class=key>3 秒</b>押す → 10 分間できる</li><li>画面の差し替え: SW2 を <b class=key>3 秒</b>押す → 10 分間できる</li>" \
"<li>ファームの USB 更新: SW2 を <b class=key>10 秒</b>押し続ける → 更新モードに入る</li></ul><small>短く押して離すと、今までどおりロック解除と全消灯です。</small></section>" \
"<div class=st id=win></div><section><h2>画面（miseru）の差し替え</h2>" \
"<p>いまの画面: <span id=uiinfo></span><br>開く: <a id=uiurl target=_blank></a></p>" \
"<label>miseru で <code>npm run build:box</code> した <b>dist/box</b> フォルダを選ぶ<input type=file id=dir webkitdirectory multiple></label>" \
"<button id=up class=main>アップロード</button><button id=reset>内蔵の画面に戻す</button><p class=m id=um></p></section>" \
"<form id=f><section><h2>PIN（miseru の Admin 用）</h2>" \
"<div class=pinst id=pinst></div><p>初期値は <b class=key>1234</b> です。いまの PIN は要りません（忘れたら新しく入れるだけ）。PIN はファームを更新しても残ります（設定は別の場所に保存。CubeProgrammer で Full chip erase をしたときだけ初期値に戻る）。SW2 を押したまま電源を入れ、そのまま 1.5 秒押し続けると（LED 2 つが 5 回点滅）、IP（192.168.1.223）と PIN が初期値に戻ります。</p>" \
"<label>新しい PIN（15 文字まで）<input id=newpin type=text maxlength=15 autocomplete=off></label>" \
"<button class=main id=pinbtn>PIN を変える</button><p class=m id=m></p></section></form>" \
"<section><h2>ファームの更新（USB-C）</h2><p>本体の LOCK ボタン（SW2）を <b class=key>10 秒</b>押し続けると、ファーム更新モードに入ります。<span class=warn>LAN と DMX の出力が止まり、電源を入れ直すまで戻りません（公演中は押さない）。</span>（3 秒で差し替えの窓が開き、そのまま押し続けて 10 秒で D6 STAT の点滅が止まり、LED 2 つとも消える）。" \
"J1 の USB-C で Mac とつなぎ、STM32CubeProgrammer の接続を USB にして書き込みます。電源を入れ直すと元に戻ります。</p></section>" \
"<p class=sub id=foot></p><script>" \
"const $=i=>document.getElementById(i),f=$('f');let ui_max=393200;" \
"const NB='受け付けていません。本体の LOCK ボタン（SW2）を 3 秒押し続けてから、この画面のボタンをもう一度押してください。';" \
"function msg(id,t,ok){const e=$(id);e.textContent=t;e.className='m '+(ok?'ok':'ng')}" \
"function load(){fetch('/api/settings').then(r=>r.json()).then(s=>{ui_max=s.ui_max;const o=s.ui_open>0;" \
"$('info').textContent=s.name+' / IP '+s.ip+' / 版 '+s.version;$('foot').textContent='MAC '+s.mac+' / 同時接続の上限 '+s.max_clients;" \
"$('win').className='st '+(o?'open':'closed');$('pinst').className='pinst '+(s.pin_default?'pdef':'pchg');$('pinst').textContent=s.pin_default?'いまの PIN は初期値（1234）のままです。変えることをおすすめします。':'いまの PIN は初期値から変更されています（値は表示しません）。';" \
"$('win').textContent=o?'差し替えと PIN の変更ができます（あと '+Math.ceil(s.ui_open/60)+' 分）':'いまは差し替えと PIN の変更はできません。本体の LOCK ボタン（SW2、RESET ではない方）を 3 秒押し続けると、10 分間だけできます（D6 STAT が 1 秒に 2 回点滅）。';" \
"for(const k of['up','reset','pinbtn'])$(k).disabled=!o;" \
"$('uiinfo').textContent=(s.ui=='uploaded'?'差し替えた画面（'+Math.round(s.ui_size/1024)+'KB）':'内蔵の画面')+'、上限 '+Math.round(s.ui_max/1024)+'KB';})}" \
"{const u=location.origin+'/';$('uiurl').href=u;$('uiurl').textContent=u}load();setInterval(load,5000);" \
"f.onsubmit=e=>{e.preventDefault();if(!$('newpin').value){msg('m','新しい PIN を入れてください');return}const d=new URLSearchParams();" \
"d.set('newpin',$('newpin').value);" \
"fetch('/api/pin',{method:'POST',body:d}).then(r=>r.json()).then(j=>{" \
"if(j.ok){msg('m','PIN を変えました。',1);$('newpin').value=''}else msg('m',j.error=='button'?NB:'値が正しくありません')}).catch(()=>msg('m','失敗しました'))};" \
"async function gz(b){if(!window.CompressionStream)return null;return new Uint8Array(await new Response(new Blob([b]).stream().pipeThrough(new CompressionStream('gzip'))).arrayBuffer())}" \
"const MIME={html:'text/html; charset=utf-8',js:'application/javascript',css:'text/css',svg:'image/svg+xml',json:'application/json',png:'image/png',ico:'image/x-icon',woff2:'font/woff2',webmanifest:'application/manifest+json'};" \
"$('up').onclick=async()=>{const fs=[...$('dir').files];if(!fs.length){msg('um','先にフォルダを選んでください');return}" \
"const parts=[],te=new TextEncoder();let names=[];for(const x of fs){let p=(x.webkitRelativePath||x.name).split('/');if(p.length>1)p=p.slice(1);p=p.join('/');" \
"if(p.startsWith('.')||p.includes('/.'))continue;names.push(p);const raw=new Uint8Array(await x.arrayBuffer());const z=await gz(raw);const use=z&&z.length<raw.length;const data=use?z:raw;" \
"const pb=te.encode(p),mb=te.encode(MIME[p.split('.').pop()]||'application/octet-stream');const h=new Uint8Array(1+pb.length+1+mb.length+5);let i=0;" \
"h[i++]=pb.length;h.set(pb,i);i+=pb.length;h[i++]=mb.length;h.set(mb,i);i+=mb.length;h[i++]=use?1:0;new DataView(h.buffer).setUint32(i,data.length,true);parts.push(h,data)}" \
"if(!names.includes('index.html')){msg('um','index.html がありません。dist/box フォルダを選んでください');return}" \
"const blob=new Blob(parts);if(blob.size>ui_max){msg('um','大きすぎます（'+Math.round(blob.size/1024)+'KB、上限 '+Math.round(ui_max/1024)+'KB）');return}" \
"msg('um','書き込み中…（'+Math.round(blob.size/1024)+'KB）');" \
"const r=await fetch('/api/ui',{method:'POST',body:blob}).then(r=>r.json()).catch(()=>({ok:false,error:'net'}));" \
"if(r.ok)msg('um','差し替えました。画面を開き直してください。',1);else msg('um',{button:NB,size:'大きすぎます',bundle:'中身が読めませんでした'}[r.error]||'失敗しました');load()};" \
"$('reset').onclick=async()=>{if(!confirm('内蔵の画面に戻しますか？'))return;const r=await fetch('/api/ui/reset',{method:'POST'}).then(r=>r.json()).catch(()=>({ok:false}));" \
"if(r.ok)msg('um','内蔵の画面に戻しました。',1);else msg('um',r.error=='button'?NB:'失敗しました');load()};" \
"</script></html>"
#endif
