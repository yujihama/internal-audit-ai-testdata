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

## 押印の読み取り（`押印/`）

実務版の読みにくい版（C_実務版_難）から、劣化の強い36ページ（7領域、印影104個）を選び、ページ画像を渡して印影の一覧（部署・日付・氏名）を答えさせます。正解（`gt.py`）は、同じページの読みやすい版（D_実務版_対照）の印影を拡大して目で読み取ったものです。

```
cd 押印
python cand.py && python prep.py          # 押印のあるページを洗い出し、36ページを samples/ に作る
python run.py gpt-6.2-sol raw             # ページをそのまま渡す
python run.py gpt-6.2-sol raw+unsure      # 「確信がなければ ■」の指示を追加
python run2.py gpt-6.2-sol                # 2段階（位置を答えさせ、切り出して拡大し、読み直す）
python score.py                           # 採点
```

`summary_押印.csv`：2026-11-19 に実行した全条件の、ページごとの採点結果と誤りの内容。

### 誤読を減らす（`ens.py`）

複数の読み取り結果を突き合わせ、一致した項目だけ採用し、一致しなければ「■（読めない）」にします。

```
python run.py gpt-6.2-sol raw+roster      # 名簿（名字と部署の候補）を指示文に付けて、そのまま渡す
python run.py gpt-6.2-sol auto+roster     # 同じく、自動の前処理をしてから
python run.py gpt-6.2-sol up2+roster      # 同じく、2倍に拡大してから
python ens.py all gpt-6.2-sol__raw+roster gpt-6.2-sol__auto+roster gpt-6.2-sol__up2+roster   # 3通りが全部一致した項目だけ採用
python ens.py 2   gpt-6.2-sol__raw+roster gpt-6.2-sol__auto+roster gpt-6.2-sol__up2+roster   # 2通り以上の一致で採用
```

名簿は `variants.py` の `roster` で、正解に出てくる名字・部署に、出てこない名字20・部署8を混ぜたものです。

### 名簿を使わずに誤読を減らす（自動の名簿・確信度）

```
python run.py gpt-6.2-sol raw && python run.py gpt-6.2-sol auto && python run.py gpt-6.2-sol up2   # 1回目（3通り）
python run.py gpt-6.2-sol raw+self && python run.py gpt-6.2-sol auto+self   # 2回目：1回目で3通りが一致した名字・部署を、同じ領域の候補として渡す
python ens.py all gpt-6.2-sol__raw+self gpt-6.2-sol__auto+self              # 2通りが一致した項目だけ採用
python run.py gpt-6.2-sol raw+conf                                          # 項目ごとの確信度を答えさせる
python ana.py                                                               # 設定（detail・effort）、自動の名簿、確信度、モデル間の照合の集計
python cost.py                                                              # .budget_start より後の実行の推定額
```
