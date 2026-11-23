#!/usr/bin/env python3
"""ODE-DIY の sACN（E1.31）試験。ユニバース 1 をマルチキャスト（239.255.0.1）で 5 秒送り、
ch1〜3 を 0→255 に動かしてから Stream_Terminated を送る。
使い方: python3 sacn_test.py            （マルチキャスト）
        python3 sacn_test.py unicast    （192.168.1.223 へ直接）"""
import socket, struct, sys, time
BOX = '192.168.1.223'
def e131(seq, vals, opt=0, u=1):
    p = bytearray(638); p[0:2] = b'\x00\x10'; p[4:16] = b'ASC-E1.17\x00\x00\x00'
    struct.pack_into('>HI', p, 16, 0x7000 | (638 - 16), 4)
    p[22:38] = b'ODE-sacn-test-01'
    struct.pack_into('>HI', p, 38, 0x7000 | (638 - 38), 2)
    p[44:52] = b'sacntest'
    p[108] = 100; p[111] = seq & 255; p[112] = opt; struct.pack_into('>H', p, 113, u)
    struct.pack_into('>H', p, 115, 0x7000 | (638 - 115)); p[117] = 2; p[118] = 0xa1
    struct.pack_into('>HHH', p, 119, 0, 1, 513); p[125] = 0
    p[126:126 + len(vals)] = bytes(vals); return bytes(p)
uni = len(sys.argv) > 1 and sys.argv[1] == 'unicast'
dst = (BOX if uni else '239.255.0.1', 5568)
probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); probe.connect((BOX, 5568)); me = probe.getsockname()[0]
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_IF, socket.inet_aton(me))
s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 4)
print(f'送り元 {me} → {dst[0]}（{"ユニキャスト" if uni else "マルチキャスト"}）、ユニバース 1')
for i in range(110):
    v = min(255, i * 255 // 100)
    s.sendto(e131(i, [v, v, v]), dst); time.sleep(0.045)
print('ch1〜3 = 255 で止めました。3 秒後に終了を送ります'); time.sleep(3)
for i in range(3): s.sendto(e131(200 + i, [255, 255, 255], 0x40), dst); time.sleep(0.05)
print('Stream_Terminated を送りました（ロックが外れて 0 に戻るはず）')
