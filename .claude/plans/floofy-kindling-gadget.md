# 国旗当てクイズ MVP 実装計画

## Context

SPEC.md にまとめられた方針検討（Webアプリ/Python/Flask+Jinja2 SSR/pHash類似度/OSS国旗画像セット/最小MVP）を受けて、次のアクションである「未決定論点のヒアリング→実装計画の確定」を行うフェーズ。今回のヒアリングで以下が決定した。

- Webフレームワーク: **Flask**
- 国旗データ管理: **JSONファイル**
- pHash事前計算: **アプリ起動時に毎回計算**（画像ファイルからハッシュを計算し、メモリ上に保持。ペアワイズ距離の事前計算はしない）
- 誤答選択肢の選び方: **距離順位ベース**（閾値ではなく「距離が近い順のN位」で難易度を制御）
- 対象国数: **知名度の高い約50ヶ国に絞る**（全249国はデータ精度リスクとボリュームの観点で見送り）

現状リポジトリにはアプリコードが一切なく（devcontainer/CI設定のみ）、このセッションでMVP一式（ディレクトリ構成・データ・ロジック・ルーティング・テンプレート・テスト）をゼロから実装する。

## ディレクトリ構成

```
flag-similarity/
├── requirements.txt          # Flask, Pillow, imagehash
├── app.py                    # Flaskアプリ本体（ルーティング）
├── flagquiz/
│   ├── __init__.py
│   ├── flags.py              # data/flags.json のロード、Flagデータクラス
│   ├── similarity.py         # 起動時pHash計算、距離計算
│   └── question.py           # 出題生成（正解1+ダミー3、難易度別ランク帯）
├── data/
│   └── flags.json            # [{"code": "jp", "name_ja": "日本", "name_en": "Japan"}, ...] 約50件
├── static/
│   └── flags/                # {code}.png （flag-icons からベンダリング）
├── templates/
│   ├── base.html
│   ├── quiz.html              # 出題画面（4択フォーム + 難易度セレクタ）
│   └── result.html            # 正誤結果画面
└── tests/
    ├── test_flags.py
    ├── test_similarity.py
    ├── test_question.py
    └── test_app.py            # Flask test client でのルーティングE2E
```

## 主要ロジック設計

### `flagquiz/flags.py`
- `load_flags() -> list[Flag]`: `data/flags.json` を読み込み、`code`/`name_ja`/`name_en` を持つ `Flag` (dataclass) のリストを返す。
- `get_flag(code)`: コードから1件取得。

### `flagquiz/similarity.py`
- アプリ起動時（`app.py` 側で一度）に `static/flags/*.png` を全て開いて `imagehash.phash()` を計算し、`dict[code, ImageHash]` を保持。
- `distance(hash_a, hash_b) -> int`: `imagehash` のハミング距離（`a - b` 演算子）をラップ。
- `ranked_by_similarity(code, hashes) -> list[str]`: 指定コード以外の全コードを、pHash距離が近い順にソートしたリストを返す。

### `flagquiz/question.py`
- 難易度ごとのランク帯（0-indexed、対象49ヶ国想定）:
  - `hard`: 上位 0〜2位（最も似ている3ヶ国をそのままダミーに採用）
  - `normal`: 上位 3〜14位からランダムに3つ
  - `easy`: 上位 15位以降からランダムに3つ
- `generate_question(difficulty="normal") -> Question`: 正解をランダムに1件選出 → `ranked_by_similarity` で距離順位リスト取得 → 難易度帯からダミー3件を抽出 → 正解+ダミーをシャッフルして返す（`Question` は正解code・選択肢4件・difficultyを持つ）。
- 国数が約50と少なくランク帯は常に3件以上確保できるため、「候補3件未満」の閾値ベース特有のエッジケースは設計上発生しない（rank-based を選んだ理由の一つ）。

### `app.py` （ルーティング）
- アプリ起動時に `similarity` の起動時ハッシュ計算を一度実行し、`app.config` 等に保持。
- `GET /`: クエリパラメータ `difficulty`（デフォルト `normal`）を見て `generate_question()` を実行。正解codeと選択肢をFlask `session` に保存し、`quiz.html` をレンダリング（国旗画像+4択ボタン+難易度セレクタ）。
- `POST /answer`: フォームで送信された選択国コードを `session` の正解と比較し、正誤・正解国名・選んだ国名を `result.html` にレンダリング。「次の問題へ」リンクは `GET /` （現在の difficulty を維持）。
- `session` を使うのは、正解をHTMLソースに露出させず、DB無しでシンプルに状態を持ち回せるため（`app.secret_key` は開発用に固定値、`.env` 化は将来課題として留保）。

## データ準備（国旗画像・国名リスト）

1. `git clone --depth 1 https://github.com/lipis/flag-icons.git` を一時ディレクトリに実行（devcontainerのファイアウォールで github.com は許可ドメイン）。取得できない場合はその場で報告し対応を相談する。
2. リポジトリ内の PNG（4x3、正方形ではなく国旗らしい縦横比のもの）から、対象約50ヶ国分の `{code}.png` を `static/flags/` にコピー。
3. `data/flags.json` に対象50ヶ国（国連加盟の主要国・知名度の高い国を中心に）の `code`（ISO 3166-1 alpha-2小文字）・`name_ja`・`name_en` を作成。
4. 一時cloneディレクトリは作業後に削除。ライセンス（MIT）情報は `static/flags/` 近くに `LICENSE` または `README` として一言残す。

## requirements.txt

```
Flask
Pillow
imagehash
```
（テスト用の `pytest`・`ruff` はCI側で別途インストールされる想定に合わせ、requirements.txtには含めない）

## テスト方針（pytest）

- `test_flags.py`: `flags.json` の各エントリに対応する画像ファイルが `static/flags/` に存在すること、`code` に重複がないこと。
- `test_similarity.py`: 同一画像同士の距離が0になること、既知に似た2旗・似ていない2旗で大小関係が直感と矛盾しないこと（極端なケースのみ検証）。
- `test_question.py`: 生成された `Question` で正解が選択肢に含まれる・重複がない・4件であること、`hard` の平均距離が `easy` の平均距離より小さいこと（ランク帯ロジックの検証）。
- `test_app.py`: Flask test client で `GET /` が200かつ4択が描画されること、正解/不正解それぞれのケースで `POST /answer` が期待通りの結果ページを返すこと。

## 実装ステップ（このセッション内で順に進める）

1. 雛形: `requirements.txt`, ディレクトリ作成, 最小 `app.py`（`/` だけの疎通確認）
2. データ取得: flag-icons クローン→画像ベンダリング、`data/flags.json` 作成
3. `flagquiz/flags.py` 実装 + テスト
4. `flagquiz/similarity.py` 実装 + テスト
5. `flagquiz/question.py` 実装 + テスト
6. `app.py` 本実装（ルーティング・session）+ `templates/*.html`
7. `test_app.py` 実装
8. `pytest` / `ruff check .` を通してグリーン確認、`flask run` で簡易動作確認（`curl` でGET/POSTを通す）

## 検証方法

- `pytest` を実行し全テストがパスすること
- `ruff check .` でlintエラーがないこと
- `flask --app app run` でローカル起動し、`curl -c cookies.txt http://127.0.0.1:5000/` → 応答に4つの選択肢が含まれること、`curl -b cookies.txt -X POST -d "choice=<code>" http://127.0.0.1:5000/answer` で正誤結果が返ること、を確認
