# GLB と寸法を ode_revB_case.html に埋め直す
import base64, json, re
p = 'ode_revB_case.html'; s = open(p).read(); d = json.load(open('dims.json'))
a = base64.b64encode(open('case_assembly.glb', 'rb').read()).decode()
e = base64.b64encode(open('case_exploded.glb', 'rb').read()).decode()
s = re.sub(r'const GLB=\{asm:"[^"]*",exp:"[^"]*"\}', lambda m: f'const GLB={{asm:"{a}",exp:"{e}"}}', s)
s = re.sub(r'(<tr><td>外形（幅 × 奥行き × 高さ）</td><td class="n">)[^<]*', lambda m: m.group(1) + f"{d['outer_w']} × {d['outer_d']} × {d['outer_h']}", s)
s = re.sub(r'(<tr><td>前後の側板の幅 / 左右の側板の長さ</td><td class="n">)[^<]*', lambda m: m.group(1) + f"{d['front_back_wall_w']} / {d['side_wall_d']}", s)
s = re.sub(r'const C=\[[-\d.]+,20,-[\d.]+\]', f"const C=[{d['outer_w']/2},20,-{d['outer_d']/2}]", s)
open(p, 'w').write(s)
