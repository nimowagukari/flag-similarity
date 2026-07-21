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

## 開発環境（隔離・権限制御）

AIエージェント(Claude Code)を最大限活用しつつ、セキュリティ観点で安全に使えるよう開発環境を整備した。当初はDevcontainer隔離＋iptablesファイアウォール＋ネイティブサンドボックス検討の多層防御を志向していたが、2026-07-12に**開発効率を優先し、Devcontainerによる隔離のみを残してファイアウォールとネイティブサンドボックスは廃止**する方針に転換した（背景は後述）。

| 観点 | 決定 |
| --- | --- |
| 隔離の方式 | Devcontainer（Docker）。Claude Code自身もコンテナ内で実行する（ホストでは動かさない） |
| コンテナのベース | `python:3.12-slim` + `git`/`gh`/`tmux`/`jq`、non-rootユーザー`vscode`、`/workspaces/flag-similarity`で作業 |
| Claude Codeのネイティブサンドボックス | 廃止（2026-07-12）。`bubblewrap`/`socat`をイメージから除去し、`seccomp=unconfined`指定も撤去 |
| 外部ドメインへの通信制限 | 廃止（2026-07-12）。`.devcontainer/init-firewall.sh`を削除し、コンテナからの外部通信を無制限に変更 |
| permission.deny/ask | 破壊的操作（`rm -rf`、`git push --force`、`git reset --hard`等）は`deny`、`pip install`等は`ask`（要確認）。今回のセキュリティ緩和方針とは別軸のため維持 |
| git管理化 | 2026-07-11に着手。`git init`＋GitHubリポジトリ作成済み（[nimowagukari/flag-similarity](https://github.com/nimowagukari/flag-similarity)、public） |
| CIスコープ | GitHub Actions（`.github/workflows/ci.yml`）でlint(ruff)/test(pytest)を自動実行。pytestは`python -m pytest`で実行（`pytest`直呼びだとリポジトリルートがsys.pathに乗らずModuleNotFoundErrorになるため修正済み） |
| devcontainer内のツール可用性 | Docker・Terraform・AWS CLIは標準では入っていない（意図的な最小構成）。Dockerイメージのbuild/run検証は**ホスト側**で行う運用（ホストにDocker Desktop導入済み）。Terraform（`tfswitch`経由）とAWS CLIは本番リリース対応のため`devcontainer.json`の`features`で追加済み |
| `~/.claude`の永続化 | ワークスペース直下（`/workspaces/flag-similarity`、`.claude/plans/`含む）はホストからのbind mountで永続化される。ホームディレクトリ配下（`~/.claude/projects/`以下のセッション履歴・メモリ、認証情報等）は当初コンテナ再ビルドで消去される問題があったが、2026-07-11に`devcontainer.json`へ名前付きボリューム（`mounts`で`/home/vscode/.claude`にマウント）を追加し解消。**再ビルドを行っても`~/.claude`の内容（セッション履歴・メモリ・認証情報）は名前付きボリューム側に残るため引き継がれる**（要: 反映にはVS Code「Rebuild Container」実行が必要。ボリュームの初回作成時はDockerfileで事前作成した`vscode`所有の空ディレクトリの内容・権限がそのままコピーされる） |

### 開発環境に関する決定の背景・理由

- **ファイアウォール・ネイティブサンドボックスを廃止した理由（2026-07-12）**: 本番リリース作業（AWS SSO、Terraform、各種AWS APIアクセス）を進める中で、ドメイン許可リストの追随（IPスナップショット方式によるSTS等のIPローテーション問題等）が繰り返し発生し、都度スクリプト修正・コンテナ再構築が必要になる運用コストが開発速度のボトルネックになっていた。個人開発でリスク許容度も高いため、厳密な多層防御より開発効率を優先し、Devcontainerによる「Claude Codeをホストで直接動かさない」という最低限の隔離のみを残す方針に転換した。
- **Devcontainer隔離は維持する理由**: AIのBashコマンド実行をコンテナに閉じ込めること自体はコストが低く、ホスト環境を汚染・破壊するリスクを避けられるため、これだけは残す。
- **permission.denyとaskを使い分ける理由**: 破壊的・復元困難な操作（`rm -rf`、force push等）は問答無用で拒否(`deny`)する一方、`pip install`等の通常の開発操作まで拒否すると生産性を損なうため、確認(`ask`)に留めた。今回の方針転換後もこの区分は維持する。

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
| ~~Function URL~~ → API Gatewayカスタムドメイン | ~~API Gatewayは使わずLambda Function URL（`authorization_type=NONE`）でシンプルに公開~~ → 2026-07-19に方針転換。API Gateway (HTTP API) + カスタムドメインでの公開に変更（詳細は下記「公開経路の変更」参照） |

詳細な実装計画は `.claude/plans/vivid-watching-wigderson.md` に記載（ワークスペース内で永続化されるため、新セッションでも参照可能）。

### 進捗状況

- [x] `git init` + GitHubリポジトリ作成・push（public、[nimowagukari/flag-similarity](https://github.com/nimowagukari/flag-similarity)）
- [x] `.gitignore` 整備（`.claude/settings.local.json`含む）
- [x] `app.py`: `secret_key`を`SECRET_KEY`環境変数化（ローカル/テストは`dev-secret-key`にフォールバック）
- [x] `app.py`: `before_request`/`after_request`で`path`/`method`/`status`/`duration_ms`のJSON構造化ログを追加（CloudWatch Logsでの応答時間追跡用）
- [x] `requirements.txt`に`gunicorn`追加
- [x] `ci.yml`のpytest実行を`python -m pytest`に修正（CI失敗を解消）
- [x] `Dockerfile`作成（Lambda Web Adapter組み込み）。ホストのDocker Desktopでbuild/run/疎通確認・応答時間ログ出力を確認済み
- [x] devcontainerにTerraform（`tfswitch`）・AWS CLIを追加するため`devcontainer.json`に`features`（`ghcr.io/devcontainers/features/aws-cli:1`、`ghcr.io/devcontainers-extra/features/tfswitch:1`）を追加し、`init-firewall.sh`にAWS API向け許可ドメイン（STS/IAM/Lambda/ECR/S3/DynamoDB/Logs/CloudWatch/Budgets/SNS/SSO OIDC、`ap-northeast-1`）を追加。再ビルド後に`aws login`（SSOログイン）を実行したところ`Could not connect to the endpoint URL: "https://ap-northeast-1.signin.aws.amazon.com/v1/token"`で失敗 → SSOのブラウザ認証・トークン取得に使う`signin.aws.amazon.com`/`ap-northeast-1.signin.aws.amazon.com`が許可リストに未追加だったのが原因と判明し、`init-firewall.sh`に追加（再度**要: devcontainer再ビルド**）
- [x] `aws login`成功後、`aws sts get-caller-identity`が`Could not connect to the endpoint URL: "https://sts.ap-northeast-1.amazonaws.com/"`で失敗。調査した結果、`init-firewall.sh`のドメイン許可は文字列マッチ（完全一致/後方一致）ではなく、起動時に`dig`で解決した**IPアドレスのスナップショット**を`ipset`に登録する方式と判明。STS等のAWS地域APIエンドポイントはDNSラウンドロビンでIPが日々ローテーションするため、起動時に捕まえたIP（`52.195.200.123`）と実際にアクセス時に解決されるIP（`52.195.201.211`）が食い違い、GitHub向けの静的CIDR前提の仕組みでは対応しきれないことが根本原因
- [x] 対策として、AWS公式IPレンジ（`ip-ranges.amazonaws.com/ip-ranges.json`）による範囲一括許可（GitHubと同じ手法）を検討。ただし調査の結果、STS/IAM/Lambda/ECRなど今回必要なAPIエンドポイントには専用の`service`タグが存在せず、`AMAZON`という包括タグ（`ap-northeast-1`だけで230件、`/13`〜`/19`など非常に広いCIDRを含む＝実質そのリージョンのAWS公開IP空間の大半）にしか属さないと判明。「最小権限のドメイン許可」という既存方針とのトレードオフが大きいため、**採用しない**と決定
- [x] ~~**方針決定**: `init-firewall.sh`は変更せず、狭い個別ドメイン許可（dig方式）を維持する。~~ → IPローテーションによる接続断が繰り返し発生し開発速度のボトルネックになったため、2026-07-12に方針転換（下記参照）
- [x] **方針転換（2026-07-12）**: ファイアウォールのIPローテーション問題が再発を繰り返したこと等を踏まえ、開発効率を優先してセキュリティ制限を緩める方針に転換。`.devcontainer/init-firewall.sh`を削除し、Claude Codeのネイティブサンドボックス用パッケージ（`bubblewrap`/`socat`）と`seccomp=unconfined`指定も撤去（詳細は「開発環境（隔離・権限制御）」節参照）。ファイアウォール起因の接続断は解消したはずなので、次回再ビルド後に`aws sts get-caller-identity`が通ることを確認する
- [x] devcontainer再ビルド後、`aws sts get-caller-identity`の疎通・`tfswitch`によるterraform導入（v1.15.8）を確認
- [x] `infra/`配下にTerraform一式を作成（ECR / Lambda関数(container image, arm64, Reserved Concurrency) / Function URL(公開) / IAMロール(Lambda実行用・GitHub Actions OIDC用) / CloudWatch Dashboard・Alarm(Errors/Throttles/Duration p99) / SNS通知 / AWS Budget）。`terraform fmt`/`validate`はグリーン。**公開リポジトリとしての汎用性**を考慮し、`project_name`/`github_repository`/`notification_email`等は`variables.tf`で変数化（デフォルトは現行値、フォーク時は`terraform.tfvars`で上書き）。backend設定も`versions.tf`に直書きせず`-backend-config=backend.hcl`で注入する方式（`backend.hcl.example`をテンプレートとして同梱）
  - **状態管理の変更点**: 当初案の「S3バックエンド＋DynamoDBロック」から、Terraform 1.10+で追加されたS3ネイティブロック機能（`use_lockfile = true`）を使う方式に簡略化。DynamoDBテーブルが不要になりコスト・管理対象を削減
  - state用S3バケット自体の作成はこのTerraform/READMEの対象外とし、「バケットが作成済み・アクセス可能であること」を前提条件として`infra/README.md`に明記する方式に変更（2026-07-12、当初はAWS CLIでの作成手順をREADMEに記載していたが、バケット管理は別リポジトリ/別手段で行う想定のため削除）。ECRの初回イメージpush（Lambda関数がイメージ参照必須のため）は引き続き`infra/README.md`に手順を記載
- [x] **方針転換（2026-07-12・同日中）**: 「必要になってから変数化すればよい、まずは動くもののリリースを優先したい」というユーザー方針により、上記構成を簡略化。
  - `cloudwatch.tf`（SNS/Alarm/Dashboard）・`budget.tf`（AWS Budget）を丸ごと削除。監視・コストアラートはリリース後に追加する
  - `variable`は`aws_region`/`project_name`/`github_repository`（フォーク時に最初に書き換えるはずの値）のみ残し、`image_tag`/`lambda_memory_size`/`lambda_timeout`/`reserved_concurrency`/`log_retention_days`/`ecr_keep_images`/`github_deploy_branch`/`create_github_oidc_provider`/`existing_github_oidc_provider_arn`等はハードコードに変更（値を変える際は該当`.tf`を直接編集する運用）
  - backendの`-backend-config=backend.hcl`方式は変更なし。詳細・セットアップ手順は[infra/README.md](infra/README.md)参照
- [x] `infra/outputs.tf`の`lambda_function_name`を削除（2026-07-18）。値が`var.project_name`と同一で重複であり、`function_url`/`ecr_repository_url`/`github_actions_deploy_role_arn`と異なりREADME.mdや今後の`deploy.yml`からも参照される見込みがないと判断（`deploy.yml`はTerraformを都度実行しない軽量デプロイ経路のため、Lambda関数名は`terraform output`ではなく既知の`project_name`の値を直接使う想定）
- [x] `infra/iam.tf`の`aws_iam_openid_connect_provider.github`をこのTerraformの管理対象から外す（2026-07-18）。IAM OIDCプロバイダ（`token.actions.githubusercontent.com`）はAWSアカウント内で1つしか作成できないため、他stack/リポジトリと衝突する可能性があった。新しく`github_oidc_provider_arn`変数を追加し、既存プロバイダのARNを外部から渡す方式に変更。プロバイダ未作成の場合の`aws iam create-open-id-connect-provider`手順は`infra/README.md`の「前提条件」に追記
- [ ] `.github/workflows/deploy.yml`作成（OIDC認証 → ECR push → `aws lambda update-function-code`）。未着手のため、現状のイメージ更新は手動`docker build`→`push`→`aws lambda update-function-code`のみ
- [x] Pythonライブラリ管理を`requirements.txt`から`uv`（`pyproject.toml` + `uv.lock`）に移行（2026-07-19）。devcontainer/`Dockerfile`/CIすべてでuvバージョンを固定し（0.11.29）、`uv sync --frozen`で常に同じ断面を再現できるようにした
- [x] **公開経路の変更（2026-07-19）**: Lambda Function URLを廃止し、API Gateway (HTTP API) + カスタムドメインでの公開に変更。`infra/api_gateway.tf`を新設し、`domain_name`/`acm_certificate_arn`変数を設定するとカスタムドメインが有効になる構成（未設定時はexecute-apiのデフォルトエンドポイントのみで公開）。ACM証明書の発行・DNS検証やDNSレコード作成はこのTerraformの管理対象外とし（`github_oidc_provider_arn`と同じ考え方）、証明書ARNを外部から受け取る形にして責務を分離した。実際に`flag-similarity.nimowagukari.net`ドメインを取得し、Terraform apply・カスタムドメインでのcurl疎通確認（200応答）まで完了。CI/CD経由での反映時間確認は`deploy.yml`が未着手のため未実施
- [x] **P1-1対応: セッションCookieの正解平文化を解消（2026-07-21）**: 下記「宣伝前のリスク洗い出し」#1への対応。方式は(a)Cookie自体をFernetで暗号化する案を採用（(b)出題IDのみ渡しサーバー側メモリ保持案は、Lambdaが複数インスタンスに分散実行されるため出題時と回答時で別インスタンスに割り振られると誤判定/エラーになりうると判断し不採用。共有ストア(DynamoDB等)を使えば解決するが、追加インフラ・コストを避けたい方針と衝突するため）。`flagquiz/crypto.py`に`build_fernet(secret_key)`を追加し、既存の`SECRET_KEY`からFernet鍵を導出（鍵管理を増やさないための簡略化）。`app.py`の`session["correct_code"]`（平文）を`session["correct_token"]`（`FERNET.encrypt`した値）に変更し、`/answer`側で`FERNET.decrypt`して復号。依存関係に`cryptography`を追加（`uv add cryptography`）。テスト（`tests/test_app.py`）もセッションから直接`correct_code`を読む箇所を`FERNET.decrypt`経由に修正し、Set-Cookieに正解の平文が含まれないことを検証する回帰テストを追加。`pytest`（16件）・`ruff check .`はグリーン
- [x] **P1-1修正を本番反映（2026-07-21）**: `deploy.yml`未着手のため、手動で`docker build`→ECR `bootstrap`タグへpush→`aws lambda update-function-code`を実施。ECRはタグ可変(MUTABLE)だがLambdaは一度解決したdigestをキャッシュしタグの向き先変更を自動追随しないため、同じ`:bootstrap`タグに新イメージをpushしただけでは反映されず、`update-function-code`の実行が必須と判明（この一連の挙動を確認できたこと自体もこの回の学び）。update後の1回目のリクエストはコールドスタートで10秒タイムアウトし500応答になったが、これはP3リスク#7（コールドスタート時のpHash再計算）であり2回目以降は200で安定。本番URLで出題→回答のE2E疎通を確認し、Set-Cookieに`correct_token`（暗号化済み）のみが含まれ正解の平文が出ないことも確認済み

### 次のアクション（URL公開に向けたリスクの修正）

下記「宣伝前のリスク洗い出し」で挙げたP1・P2への対応を優先する。

1. ~~**P1-1**: セッションCookieに正解が平文で入っている問題を解消する（クライアントには出題ID(ランダムトークン)のみ渡し、正解はサーバー側で保持する方式へ設計変更）~~ → 2026-07-21対応済み（Fernet暗号化方式。詳細は上記進捗表参照）
2. **P1-2**: 宣伝規模に応じて`reserved_concurrent_executions`を一時的に引き上げる運用を決める
3. **P1-3**: 最低限のCloudWatch Alarm（Lambda Errors）・AWS Budgetのコストアラートを再整備する
4. **P2-4**: `.github/workflows/deploy.yml`を作成し、バグ修正を即座に反映できる経路を作る（上記進捗の通り未着手）
5. **P2-5**: `templates/base.html`にviewport metaタグを追加する
6. P3の項目（Cookie Secure属性、コールドスタート時のpHash再計算、`app.run(debug=True)`の環境変数化）は宣伝後の状況を見て判断

## 宣伝前のリスク洗い出し（2026-07-18セッション、2026-07-19時点の状況を反映）

デプロイ済みアプリ（カスタムドメイン: `https://flag-similarity.nimowagukari.net/`。2026-07-18時点ではLambda Function URLで公開していたが、2026-07-19にAPI Gatewayカスタムドメインへ移行済み。`curl`で200応答を確認済み）を実際に確認し、コード・Terraform設定を確認した上でのリスク一覧。優先度順（P1=公開前に必ず潰す、P2=公開直後に手当てすべき、P3=様子見で可）。下記のリスク自体（#1〜#8）は2026-07-18時点のもので、公開経路の変更後も未解消のまま残っている。

### P1: 公開前に必ず潰すべきもの

| # | リスク | 詳細・再現方法 | 対応案 |
| --- | --- | --- | --- |
| 1 | ~~**セッションCookieに正解が平文で入っており誰でも読める**~~ **→ 2026-07-21対応済み** | Flaskの`session`はデフォルトで「署名付きだが暗号化はしていないBase64」。`/`にアクセスして返る`Set-Cookie`をBase64デコードすると `{"correct_code":"ae","difficulty":"normal"}` がそのまま見える（実機で確認済み）。ブラウザの開発者ツールでCookieを見るだけで正解が分かるため、クイズとして成立しない。技術に明るい層（SRE/インフラ界隈）に宣伝するなら真っ先に気づかれ、信頼を損なう | 案(a)のCookie自体をFernetで暗号化する方式を採用し実装済み。`flagquiz/crypto.py`＋`app.py`の`correct_token`セッションキー参照。案(b)（出題IDのみ渡しサーバー側メモリ保持）はLambdaの複数インスタンス分散実行と相性が悪い（出題時と回答時で別インスタンスに割り振られると誤判定になりうる）ため不採用とした |
| 2 | **Reserved Concurrency=5がスループット上限かつレート制限が一切ない** | Lambda Function URLは`authorization_type=NONE`で誰でも無制限にリクエスト可能。同時実行数の上限は`reserved_concurrent_executions=5`のみで、これは「コスト上限」であると同時に「同時に5人しか捌けない」という上限でもある。宣伝してアクセスが集中すると、正規ユーザーがスロットリング（429/エラー）される。「宣伝の効果を自分で潰す」矛盾したトレードオフになっている | 宣伝規模を見積もった上で`reserved_concurrent_executions`を一時的に引き上げる（例: 20〜50）。恒久的な対策が要らないなら「宣伝直前に上げて、落ち着いたら戻す」運用でも可 |
| 3 | **監視・アラートが皆無** | `cloudwatch.tf`/`budget.tf`は「まず動くものを優先」で意図的に削除済み（2026-07-12の方針転換）。宣伝後にエラー多発やコスト急増が起きても気づく手段がCloudWatch Logsを手動で見る以外にない | 最低限、(a) Lambda Errorsのアラーム、(b) AWS Budgetのコストアラートだけは宣伝前に再度用意する。Dashboard等は後回しで良い |

### P2: 公開直後の運用に支障が出るもの

| # | リスク | 詳細 | 対応案 |
| --- | --- | --- | --- |
| 4 | **バグ修正を即座に反映する経路がない** | `.github/workflows/deploy.yml`が未作成（本メモの進捗表でも未着手）。現状の更新手段は手動`docker build`→`push`→`aws lambda update-function-code`のみ。宣伝直後に軽微な不具合が見つかっても復旧が遅れる | 宣伝前に`deploy.yml`を作成し、mainマージで自動反映される状態にしておく |
| 5 | **モバイル表示が最適化されていない** | `templates/base.html`に`<meta name="viewport">`が無い。SNS経由の流入はスマホが多いと想定されるが、現状は縮小表示になりうる | `viewport` metaタグを追加するだけの軽微な修正 |

### P3: 様子見で良いもの

| # | リスク | 詳細 |
| --- | --- | --- |
| 6 | Cookieに`Secure`属性が付いていない（`HttpOnly`のみ）。Function URLは常時HTTPSなので実害は小さいが、`app.config["SESSION_COOKIE_SECURE"] = True`を明示しておくと安全側 |
| 7 | scale-to-zero構成のため、コールドスタート時に毎回`static/flags/*.png`からpHashを再計算する（`compute_hashes`）。閑散期明けの初回アクセスの応答が目立って遅くなる可能性 |
| 8 | `app.py`末尾の`app.run(debug=True)`はローカル実行専用（`if __name__ == "__main__"`配下で本番のgunicorn経路では通らない）。実害はないが将来の事故防止のため環境変数化を検討 |

### 対応方針（未決定・次回相談）

上記のうちP1の3件、特に#1（Cookieで正解が見える）は仕様・設計の変更を伴うため、着手前にユーザーと実装方針をすり合わせる必要がある。
