# 国旗の国名当てクイズアプリ — 仕様検討メモ

## Context

国旗画像の類似度を画像分析で判定し、選択肢の難易度を調整できる「国名当てクイズ」を作りたい。
ユーザーはインフラ・サーバー・SREが専門でアプリ開発（コーディング）は弱いため、シンプルな技術スタックを使いながらコーディングスキル向上を伴走してもらうことを目的としている。

このメモは、実装に入る前の「仕様をどう決めるか」のヒアリングで確定した方針をまとめたもの。次回以降のセッションで再利用し、ここから設計・実装を進める想定。

## 確定した方針（ユーザーへのヒアリング結果）

| 観点 | 決定 |
| --- | --- |
| 動作環境/プラットフォーム | Webアプリ（バックエンドあり、API的構成も可） |
| メイン言語・技術スタック | Python |
| フロントエンドの作り方 | サーバーサイドレンダリング（Jinja2）。SPA的なJSは使わない方針 |
| 国旗画像の類似度判定手法 | 知覚的ハッシュ（pHashなど）。Pillow + `imagehash` ライブラリを想定 |
| 国旗画像データの入手元 | オープンソースの国旗画像セットを使う。ISO 3166-1 alpha-2コードでファイル名管理（実際の入手元は下記「未決定論点の決定」を参照） |
| 最初に作る範囲（MVP） | 最小限のみ。「4択クイズ + 類似度による選択肢の難易度調整」のコア機能だけ。スコア記録や複数モードなどは後回し |

## 決定の背景・理由

- **Webアプリ(API付き) を選んだ理由**: SREの知識（デプロイ・監視・DB等）を活かしやすく、本格的なアプリ開発の練習になる。静的サイトやCLIより学習効果が高いと判断。
- **Pythonを選んだ理由**: 画像処理ライブラリ（Pillow, imagehash, OpenCV）が充実しており、インフラ系ツールでも触れる機会が多く学習コストが低い。
- **SSR(Jinja2)を選んだ理由**: JSをほぼ書かずにPythonの学習に集中できる。フォーム送信→ページ遷移というシンプルな流れで、初学者に分かりやすい。
- **pHashを選んだ理由**: 画像を小さなハッシュ値に変換して距離計算するだけで類似度が出せる。軽量・高速でライブラリ1つで実装可能。デフォルトとして推奨し採用。
- **オープンソース国旗画像セットを選んだ理由**: 外部API依存（ネットワーク障害・レート制限）を避け、pHash計算が安定する。ライセンス確認の上でローカルにベンダリングする。
- **MVP最小スコープを選んだ理由**: まず動くものを早く作り、そこから一緒に拡張していく方が学習サイクルとして回しやすい。

## 未決定論点の決定（2026-07-11 セッション）

| 観点 | 決定 |
| --- | --- |
| Webフレームワーク | Flask |
| 国旗データの管理方法 | JSONファイル（`data/flags.json`）。約50ヶ国（知名度の高い国に限定、全249国は見送り） |
| 国旗画像データの実際の入手元 | flag-icons はSVGのみ配布のためPNG化には不向きと判明。代わりに `gosquared/flags`（MITライセンス、PNG・ISO 3166-1 alpha-2ファイル名）をベンダリング |
| pHash事前計算の仕組み | アプリ起動時に `static/flags/*.png` から毎回計算しメモリ保持（ペアワイズ距離は事前計算せず、出題のたびにO(n)で計算） |
| 誤答選択肢選定アルゴリズム | 距離順位ベース。`hard`=上位0-2位、`normal`=上位3-14位、`easy`=15位以降からランダム抽出。国数が50弱のため「候補3件未満」のエッジケースは発生しない |
| ルーティング設計 | `GET /`（出題、`?difficulty=`で難易度指定、Flask sessionに正解を保持）、`POST /answer`（採点・結果表示） |
| ディレクトリ構成・依存ライブラリ | 下記「実装済み構成」を参照。`requirements.txt` は Flask / Pillow / imagehash のみ |
| テスト方針 | pytestで `flagquiz/` 配下（データロード・pHash距離・出題ロジック）とFlaskルーティング（test client）を単体〜結合テスト |
| 実装ステップ | 雛形→データ準備→flags.py→similarity.py→question.py→app.py/テンプレート→test_app.py→lint/手動確認、の順で1セッション内で実装 |

## 実装済み構成（MVP）

```
flag-similarity/
├── requirements.txt
├── app.py
├── flagquiz/{flags,similarity,question}.py
├── data/flags.json          # 50ヶ国
├── static/flags/{code}.png  # gosquared/flags からベンダリング（LICENSE-flags.txt同梱）
├── templates/{base,quiz,result}.html
└── tests/test_{flags,similarity,question,app}.py
```

MVPのコア機能（4択クイズ＋pHash類似度による難易度調整）は実装済み。`pytest`（15件）・`ruff check .` はグリーン。`flask --app app run` での起動・curlでの一連の動作確認済み。

## 今後の論点（未着手）

- スコア記録・複数モード等のMVP後の拡張（意図的にスコープ外としていた範囲）
- 対象国を約50ヶ国から広げる場合のデータ拡充方針

## 開発環境（隔離・サンドボックス・権限制御）

AIエージェント(Claude Code)を最大限活用しつつ、セキュリティ観点で安全に使えるよう、以下の二層防御の開発環境を整備した。

| 観点 | 決定 |
| --- | --- |
| 隔離の方式 | Devcontainer（Docker）。Claude Code自身もコンテナ内で実行する（ホストでは動かさない） |
| コンテナのベース | `python:3.12-slim` + `iptables`/`ipset`等（ファイアウォール用）+ `git`/`gh`/`tmux`、non-rootユーザー`vscode`、`/workspaces/flag-similarity`で作業 |
| Claude Codeのネイティブサンドボックス | 廃止。デフォルトのコンテナ設定ではseccompの制約によりbubblewrapベースのサンドボックスが動作せず、`unconfined`にすることはコンテナのセキュリティを緩めるリスクがあるため採用しない |
| 外部ドメインへの通信制限 | `.devcontainer/init-firewall.sh`（iptables + ipset）で実現。公式ドキュメントの実装例を参考に、コンテナ起動時にデフォルトDROPのファイアウォールを構成し、許可ドメイン（GitHub API/Web/Git、npm registry、Anthropic API等）のみ通信を許可する |
| permission.deny/ask | 破壊的操作（`rm -rf`、`git push --force`、`git reset --hard`等）は`deny`、`pip install`等は`ask`（要確認） |
| git管理化 | 2026-07-11に着手。`git init`＋GitHubリポジトリ作成済み（[nimowagukari/flag-similarity](https://github.com/nimowagukari/flag-similarity)、public） |
| CIスコープ | GitHub Actions（`.github/workflows/ci.yml`）でlint(ruff)/test(pytest)を自動実行。pytestは`python -m pytest`で実行（`pytest`直呼びだとリポジトリルートがsys.pathに乗らずModuleNotFoundErrorになるため修正済み） |
| devcontainer内のツール可用性 | Docker・Terraform・AWS CLIは標準では入っていない（意図的な最小構成）。Dockerイメージのbuild/run検証は**ホスト側**で行う運用（ホストにDocker Desktop導入済み）。Terraform（`tfswitch`経由）とAWS CLIは本番リリース対応のため`devcontainer.json`の`features`で追加中（後述） |
| `~/.claude`の永続化 | ワークスペース直下（`/workspaces/flag-similarity`、`.claude/plans/`含む）はホストからのbind mountで永続化されるが、ホームディレクトリ配下（`~/.claude/projects/`以下のセッション履歴・メモリ）はコンテナ再ビルドで消去される。**再ビルドを行うとClaude Codeのセッション・会話履歴・メモリは引き継がれない**ため、進行中の作業内容はこのSPEC.mdなどワークスペース内のファイルに記録し、再ビルド後の新セッションはSPEC.mdを読んで状況を復元する |

### 開発環境に関する決定の背景・理由

- **Claude Codeのネイティブサンドボックスを廃止した理由**: bubblewrapはunprivileged user namespaceに依存するが、デフォルトのコンテナ設定（seccompプロファイル有効）では必要なsyscallが制限され動作しない。`seccomp=unconfined`にすれば動作させられるが、コンテナのシステムコールフィルタを丸ごと外すことになりリスクが大きいため、恒久的に不採用と判断した。
- **`.devcontainer/init-firewall.sh`によるiptables/ipsetベースのファイアウォールを採用した理由**: ネイティブサンドボックスが使えないため、Claude Codeの`network.allowedDomains`によるアプリケーションレベルの制限に頼れない。代わりにOS（コンテナ）レベルでデフォルトDROP＋許可ドメインのみACCEPTのファイアウォールを構成し、外部通信を制限する。実装は公式ドキュメントに掲載されているiptables/ipsetパターンを参考にした。
- **Docker（外側）+ ファイアウォールスクリプト（内側）の二層構成にした理由**: コンテナがアプリの実行環境だけを隔離しても、AIのBashコマンド実行自体がホスト権限下にあると隔離効果が薄い。AIのコマンド実行そのものをコンテナに閉じ込めた上で、コンテナ内の通信もファイアウォールで許可ドメインのみに絞ることで、隔離の実効性を高めた。
- **運用上の留意点**: 許可ドメインは`init-firewall.sh`内にハードコードされているため、新しい外部サービス（例: 新しいPythonパッケージのミラー、別のAPI等）にアクセスする必要が出るたびに、スクリプトへドメイン追加とコンテナ再構築（ファイアウォール再適用）が必要になる。ドメイン単位での都度調整が発生する運用コストがある点は許容している。
- **permission.denyとaskを使い分ける理由**: 破壊的・復元困難な操作（`rm -rf`、force push等）は問答無用で拒否(`deny`)する一方、`pip install`等の通常の開発操作まで拒否すると生産性を損なうため、確認(`ask`)に留めた。

## 本番リリース計画（2026-07-11 着手）

MVP動作確認後、本番リリースに向けた作業を開始。要件は「(1) コード改修後すぐ本番反映できるシンプルなCI/CD」「(2) 個人開発のためコスト抑制・大量アクセス時のコスト高騰防止」「(3) 応答時間を含む可観測性」。

ヒアリングで確定した方針：

| 観点 | 決定 |
| --- | --- |
| ホスティング | AWS Lambda + [Lambda Web Adapter](https://github.com/aws/aws-lambda-web-adapter)（コンテナイメージ）。Flaskをほぼ無改修で実行、真のscale-to-zero、Reserved Concurrencyでコスト上限を固定 |
| IaC | Terraform（ユーザーがSRE業務で使い慣れており学習コスト最小） |
| リージョン | `ap-northeast-1`（仮決め） |
| CI/CD | GitHub Actions。lint/test（既存ci.yml）→ mainマージでECRへdocker push → `aws lambda update-function-code`で高速反映。Terraformのインフラ変更は別経路（頻度低） |
| 認証 | GitHub Actions→AWSはOIDC（長期アクセスキー不使用）。devcontainer内のterraform apply用はAWS SSO/一時トークン（`aws login`、長期キーは置かない） |
| Function URL | API Gatewayは使わずLambda Function URL（`authorization_type=NONE`）でシンプルに公開 |

詳細な実装計画は `.claude/plans/vivid-watching-wigderson.md` に記載（ワークスペース内で永続化されるため、新セッションでも参照可能）。

### 進捗状況

- [x] `git init` + GitHubリポジトリ作成・push（public、[nimowagukari/flag-similarity](https://github.com/nimowagukari/flag-similarity)）
- [x] `.gitignore` 整備（`.claude/settings.local.json`含む）
- [x] `app.py`: `secret_key`を`SECRET_KEY`環境変数化（ローカル/テストは`dev-secret-key`にフォールバック）
- [x] `app.py`: `before_request`/`after_request`で`path`/`method`/`status`/`duration_ms`のJSON構造化ログを追加（CloudWatch Logsでの応答時間追跡用）
- [x] `requirements.txt`に`gunicorn`追加
- [x] `ci.yml`のpytest実行を`python -m pytest`に修正（CI失敗を解消）
- [x] `Dockerfile`作成（Lambda Web Adapter組み込み）。ホストのDocker Desktopでbuild/run/疎通確認・応答時間ログ出力を確認済み
- [ ] **進行中**: devcontainerにTerraform（`tfswitch`）・AWS CLIを追加するため`devcontainer.json`に`features`（`ghcr.io/devcontainers/features/aws-cli:1`、`ghcr.io/devcontainers-extra/features/tfswitch:1`）を追加し、`init-firewall.sh`にAWS API向け許可ドメイン（STS/IAM/Lambda/ECR/S3/DynamoDB/Logs/CloudWatch/Budgets/SNS/SSO OIDC、`ap-northeast-1`）を追加。**反映にはdevcontainerの再ビルドが必要**（ユーザー側でVS Code「Rebuild Container」を実行）。再ビルド後、`aws login`でAWS認証、`tfswitch`でterraformバイナリを導入する
- [ ] `infra/`配下にTerraform一式を作成（ECR / Lambda関数(container image, arm64, Reserved Concurrency) / Function URL / IAMロール(Lambda実行用・GitHub Actions OIDC用) / CloudWatch Dashboard・Alarm / AWS Budget）。Terraform stateはS3バックエンド（+DynamoDBロック）を用意
- [ ] `.github/workflows/deploy.yml`作成（OIDC認証 → ECR push → `aws lambda update-function-code`）
- [ ] 動作確認（Terraform apply → Function URLへのcurl疎通 → CloudWatch Logs/Dashboardで応答時間確認 → Reserved Concurrencyによるスロットリング確認 → push後の反映時間確認）

### 次のアクション（再ビルド後）

1. `aws login`でAWS認証、`aws sts get-caller-identity`で疎通確認
2. `tfswitch`でterraformバイナリを導入
3. 上記「進捗状況」の未完了タスクを順番に進める（Terraform一式の作成から）
