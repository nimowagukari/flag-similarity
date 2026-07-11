# 本番リリース計画：AWS Lambda (+ Lambda Web Adapter) へのデプロイ

## Context

MVP実装（Flask + Jinja2 SSR の国旗クイズアプリ）は完了し、`pytest`/`ruff` はグリーン。次のステップとして本番リリースを計画する。ユーザーからのヒアリングで以下が確定した。

- **要件**: (1) コード改修後すぐ本番反映できるシンプルなCI/CD、(2) 個人開発のためコストを抑え、特に大量アクセス時のコスト高騰を防ぐ、(3) 応答時間を含む可観測性を担保する
- **ホスティング**: AWS Lambda + [Lambda Web Adapter](https://github.com/aws/aws-lambda-web-adapter)（コンテナイメージ）を採用。Flaskコードをほぼ無改修のままLambda上で動かせる。真のscale-to-zeroとReserved Concurrencyによるハードキャップで要件(2)を、API Gateway/Lambda標準メトリクスで要件(3)を、他のAWS選択肢（App Runner/EC2）より強く満たせる
- **IaC**: Terraform（ユーザーが使い慣れており、新規学習コストが最小）
- **現状の未整備事項**: このリポジトリはまだ `git init` されていない。`app.secret_key` が開発用固定値。`requirements.txt` にWSGIサーバー（gunicorn）が無い。デプロイ用Dockerfile/Terraform/GitHub Actionsは未着手

この計画は上記を踏まえ、具体的な実装ステップに落とし込んだもの。

## 全体アーキテクチャ

```
GitHub push (main)
  └─ GitHub Actions
      ├─ [ci] ruff + pytest（既存 ci.yml を流用）
      └─ [deploy] (ci成功後、mainのみ)
          ├─ OIDC で AWS IAM Role を引き受け（長期アクセスキー不使用）
          ├─ Docker build（Flask + Lambda Web Adapter）→ ECR push（tag=git sha）
          └─ aws lambda update-function-code --image-uri ...（コードのみ高速デプロイ）

Terraform（別ワークフロー／手動 apply、頻度低）
  └─ ECR repo / Lambda関数（container image, ARM64, Reserved Concurrency）
     / Function URL / IAM Role / CloudWatch Dashboard・Alarm / AWS Budget
```

**アプリデプロイ（頻繁）と インフラ変更（稀）を分離**するのがポイント。コード改修のたびに `terraform apply` を回すと遅く・リスクも増えるため、通常のリリースは ECR push + `update-function-code` の軽量パスにする。

## 実装ステップ

### 0. リポジトリ整備（前提作業）
- `git init` し、`gh repo create` でGitHubリポジトリを作成（private想定、実行時に確認）
- `.gitignore` 追加（`__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `*.pyc`, `.terraform/`, `terraform.tfstate*` 等）
- 既存コードを初回コミット

### 1. アプリ側の本番対応（最小限の変更）
- `app.py`: `app.secret_key = "dev-secret-key"` → `os.environ["SECRET_KEY"]` から取得するよう変更
- `requirements.txt`: `gunicorn` を追加（Lambda Web AdapterはHTTPサーバー越しにリクエストを転送するため、開発用Flaskサーバーではなくgunicornで起動する）
- `app.py` に軽量な `after_request` フックを追加し、`request.path` / `status` / 応答時間(ms) を構造化ログ（stdout）に出力 → CloudWatch Logsに自動収集され、Lambda標準の`Duration`メトリクスに加えてルート単位の応答時間も追える
- 起動コマンド例: `gunicorn app:app -b 0.0.0.0:8080 -w 1`（Lambdaは1リクエストずつ処理するためワーカー数は最小でよい）

### 2. コンテナ化
- リポジトリ直下に `Dockerfile` を新規作成
  - ベースイメージ: `python:3.12-slim`（または `public.ecr.aws/lambda/python`系ではなく、Lambda Web Adapterパターンに従い通常のPythonベースイメージ + アダプタ層を利用）
  - `COPY --from=public.ecr.aws/awsguru/aws-lambda-adapter:<latest> /lambda-adapter /opt/extensions/lambda-adapter`
  - アプリコード・`static/`・`templates/`・`data/` をコピー、`pip install -r requirements.txt`
  - `CMD` でgunicorn起動（ポート8080固定、`AWS_LWA_PORT`のデフォルトと一致）
- ローカルで `docker build` → `docker run` して動作確認（Lambda環境なしでも通常のHTTPサーバーとして動く＝Lambda Web Adapterの利点）

### 3. Terraformによるインフラ定義
新規ディレクトリ `infra/`（Terraform一式）を作成し、以下を定義:
- `aws_ecr_repository`（イメージ保管、ライフサイクルポリシーで古いイメージ自動削除しストレージコスト抑制）
- `aws_lambda_function`（`package_type = "Image"`、architecture = `arm64`（Gravitonでコスト・性能有利）、memory/timeoutは小さめ（例: 512MB/10秒）から開始、環境変数に `SECRET_KEY`（`random_password` リソースで生成しstateに保持）
- `aws_lambda_function_url`（`authorization_type = "NONE"`で公開。API Gatewayは使わず、要件の「シンプルさ」を優先。将来カスタムドメインや認証が必要になれば移行可能な点を明記）
- `aws_lambda_function.reserved_concurrent_executions`（例: 5。要件(2)「大量アクセスでのコスト高騰防止」のハードキャップ）
- IAM: Lambda実行ロール（最小権限）＋ GitHub Actions用のOIDC IAM Role（`sts:AssumeRoleWithWebIdentity`、ECR push・Lambda update権限のみ）
- CloudWatch: `aws_cloudwatch_dashboard`（Duration p50/p90/p99, Invocations, Errors, Throttlesのウィジェット）、`aws_cloudwatch_metric_alarm`（Errors > 0 や Duration閾値超過をSNS経由でメール通知）
- `aws_budgets_budget`（例: 月$5でアラート。コスト高騰の最終防衛線）
- Terraform state: S3バックエンド（+ DynamoDBロック）を最初に手動で1回だけ用意する必要がある点を明記

### 4. CI/CDパイプライン（GitHub Actions）
- 既存 `.github/workflows/ci.yml` の lint/test はそのまま維持
- 新規 `.github/workflows/deploy.yml` を追加:
  - トリガー: `push` to `main`、`workflow_run` で ci.yml 成功後に実行（または同一workflow内で `needs:` により連結）
  - `permissions: id-token: write` を設定しOIDC認証（`aws-actions/configure-aws-credentials`）
  - `aws-actions/amazon-ecr-login` でECRログイン
  - `docker build` → `docker push`（タグ = `${{ github.sha }}`）
  - `aws lambda update-function-code --function-name ... --image-uri ...` で即時反映（Terraform applyを介さない高速パス）
  - Terraformのインフラ変更（`infra/*.tf` 差分がある場合）は同一workflowの別jobとして `terraform plan`（PRでコメント）→ mainマージで `terraform apply` を回す運用も選択肢として明記（ここは実装時に相談）

### 5. 動作確認・検証
- ローカルDockerビルドで疎通確認 → ECRへ手動pushしてLambda関数を初回作成（Terraform apply）
- Function URLへcurlで疎通確認（`/` → 200、`POST /answer` → 正しい採点）
- CloudWatch Logsにリクエストログが出力されていること、Dashboardでレイテンシが見えることを確認
- 意図的に同時多重リクエストを送り、Reserved Concurrency設定でスロットリングされる（コストが青天井にならない）ことを確認
- GitHub Actionsでコード変更→push→数分以内に本番Function URLへ反映されることを確認（要件1の検証）

## 未確定・実装時に相談する点
- GitHubリポジトリ名・可視性（private想定で進めてよいか）
- Terraform stateのS3バケット名・リージョン（東京 `ap-northeast-1` を既定と想定）
- Reserved Concurrency・メモリサイズの初期値（上記は仮の初期値。実装時に確定）
- Terraform applyをCIで自動化するか、当面は手動applyに留めるか

## 検証方法まとめ
- `pytest` / `ruff check .`（既存、変更なし）
- `docker build . && docker run -p 8080:8080 ...` でローカル疎通
- Terraform: `terraform plan` で差分確認 → `terraform apply`
- 本番: Function URLへのcurl、CloudWatch Logs/Dashboard目視、GitHub Actionsのデプロイ所要時間計測
