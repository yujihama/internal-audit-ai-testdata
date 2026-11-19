# 画像の読み取り精度の比較（GPT系とClaude系）

解像度の低いスキャン風の証跡24枚（低解像度＋強い圧縮 7、FAX受信風 10、粗い網点 7。いずれも「人は読める」段階2）を各モデルに書き起こさせ、読みやすい版（B_対照版）のPDFの文字情報を正解として採点します。

- 採点の主な指標は「数字項目」：金額・日付・番号・型番など、数字を含む項目のうち正しく書き起こせた割合
- `summary.csv`：2026-11-19 に実行した全条件の、画像1枚ごとの採点結果

## 手順

```
python3 -m venv .venv && .venv/bin/pip install pymupdf pillow numpy opencv-python-headless httpx
.venv/bin/python prep.py                                   # サンプル24枚と正解を samples/ に作る
.venv/bin/python run.py gpt-5.4 raw                        # そのまま渡す（OpenAI。OPENAI_API_KEY が必要）
.venv/bin/python run.py gpt-5.4 auto                       # 自動の前処理をしてから渡す
.venv/bin/python run.py gpt-5.1 smooth+tile2x2             # ならし＋4分割
.venv/bin/python run.py gpt-6.2-sol raw detail=low         # 解像度の指定を変える
.venv/bin/python run.py anthropic/claude-sonnet-5.5 raw    # 名前に / があるモデルは OpenRouter 経由（OPENROUTER_API_KEY）
.venv/bin/python score.py                                  # 採点（条件ごとの一覧）
.venv/bin/python miss.py gpt-5.4__raw openai_gpt-5.4__auto # 読み落とした項目を並べて見る
```

加工名（`variants.py`）は `+` でつなげます：`raw` そのまま／`auto` 画像の状態を見て自動（白黒2値・網点ならならす、小さければ2倍に拡大）／`smooth` ならし／`up2` 2倍に拡大／`tile2x2` 重なりを付けて分割／`strict` 「知識で補正しない」指示を追加／`pdf` 元のPDFをそのまま渡す。
