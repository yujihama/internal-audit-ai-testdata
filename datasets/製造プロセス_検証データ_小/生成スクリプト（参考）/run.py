# -*- coding: utf-8 -*-
"""実務データ編の実行: python run.py <領域のキー> [段階]
段階: build（証跡の生成のみ）/ book（正解表以降のみ）/ 省略時はすべて"""
import sys, importlib, subprocess, pickle
import fw
from common import ROOT

MODS = {'itinfra': 'd1_itinfra', 'itapp': 'd2_itapp', 'mfg': 'd3_mfg', 'inv': 'd4_inv', 'const': 'd5_const'}
key = sys.argv[1]
stage = sys.argv[2] if len(sys.argv) > 2 else 'all'
m = importlib.import_module(MODS[key])
if stage in ('all', 'build'):
    DT = m.build()
    fw.finish(DT)
if stage in ('all', 'ocr'):
    r = subprocess.run([sys.executable, 'ocr_ref.py', m.NAME, f'tmp_{key}'], capture_output=True, text=True)
    print('文字読取の参考値:', r.stdout.strip().replace('\n', ' / '), r.stderr[-300:])
if stage in ('all', 'book'):
    ST = pickle.load(open(f'{ROOT}/out/tmp_{key}/state.pkl', 'rb'))
    sp = m.spec(ST)
    fw.book(sp, ST)
    c = fw.Ctx(sp)
    m.recalc(c)
    ok = fw.verify(sp, c)
    if ok:
        fw.pack(sp, [MODS[key] + '.py'])
