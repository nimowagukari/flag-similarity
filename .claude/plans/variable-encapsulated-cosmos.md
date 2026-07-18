# infra/ の簡略化（変数削減・監視リソース除外）

## Context

直前のセッションで `infra/` 配下にTerraform一式（ECR / Lambda / IAM / CloudWatch Dashboard・Alarm / SNS / AWS Budget）を作成し、パブリックリポジトリとしての汎用性を意識して主要な設定値をすべて`variable`化した。

しかし実運用を始めるにあたり、ユーザーから「必要になってから変数化すればよい。まずは動くもののリリースを優先したい」という方針転換の指示があった。ヒアリング結果は以下の通り：

- 監視系リソース（`cloudwatch.tf`＝SNS/Alarm/Dashboard、`budget.tf`＝AWS Budget）は**丸ごと除外**し、リリース後に追加する
- `variable`は `project_name` / `aws_region` / `github_repository` の3つ（＝フォーク時に最初に書き換えるはずの値）だけ残し、それ以外（`image_tag` / `lambda_memory_size` / `lambda_timeout` / `reserved_concurrency` / `log_retention_days` / `ecr_keep_images` / `github_deploy_branch` / `create_github_oidc_provider` / `existing_github_oidc_provider_arn` / `notification_email` / `duration_alarm_threshold_ms` / `budget_limit_usd`）はハードコードする
- backendの`-backend-config=backend.hcl`による外部注入方式は現状維持（変更なし）

この方針変更を`infra/`配下の既存Terraformコードに反映する。

## 変更内容

### 削除するファイル
- `infra/cloudwatch.tf`（SNSトピック・サブスクリプション、Errors/Throttles/Duration p99アラーム、Dashboard）
- `infra/budget.tf`（AWS Budget）

### `infra/variables.tf`
以下の3つだけ残す（説明・デフォルト値は現行のまま流用）:
- `aws_region`（デフォルト `"ap-northeast-1"`）
- `project_name`（デフォルト `"flag-similarity"`）
- `github_repository`（デフォルト `"nimowagukari/flag-similarity"`）

他の変数（`image_tag`, `lambda_memory_size`, `lambda_timeout`, `reserved_concurrency`, `log_retention_days`, `ecr_keep_images`, `github_deploy_branch`, `create_github_oidc_provider`, `existing_github_oidc_provider_arn`, `notification_email`, `duration_alarm_threshold_ms`, `budget_limit_usd`）は削除し、参照元では下記のようにリテラル値に置き換える。

### `infra/ecr.tf`
- `var.ecr_keep_images` → `10`

### `infra/lambda.tf`
- `var.image_tag` → `"bootstrap"`
- `var.lambda_memory_size` → `512`
- `var.lambda_timeout` → `10`
- `var.reserved_concurrency` → `5`
- `var.log_retention_days` → `14`
- ロジック・リソース構成（Function URL、公開許可、`lifecycle.ignore_changes`等）はそのまま維持

### `infra/iam.tf`
- `aws_iam_openid_connect_provider.github` の `count = var.create_github_oidc_provider ? 1 : 0` を外し、無条件作成の単一リソースにする
- `local.github_oidc_provider_arn` を廃止し、`aws_iam_openid_connect_provider.github.arn` を直接参照
- `var.github_deploy_branch` → `"main"`（`sub`条件の文字列に直書き）
- Lambda実行ロール部分は変更なし

### `infra/outputs.tf`
- `cloudwatch_dashboard_url` の output を削除（対象リソースが無くなるため）
- 他のoutput（`function_url` / `ecr_repository_url` / `lambda_function_name` / `github_actions_deploy_role_arn`）は維持

### `infra/terraform.tfvars.example`
- `aws_region` / `project_name` / `github_repository` の3項目のみに簡略化
- `notification_email` / `reserved_concurrency` / `budget_limit_usd` 等のコメントアウト例を削除

### `infra/README.md`
- 構成表からCloudWatch Dashboard/Alarm/SNS/Budgetの行を削除
- 「注意事項」からReserved Concurrency変更方法（→ `lambda.tf`を直接編集する旨に書き換え）・`notification_email`に関する記述を削除
- GitHub OIDCプロバイダの「AWSアカウントに1つまで」という制約は`variable`による切り替えが無くなった後も実際のAWS側の制約として残るため、「同一アカウントで複数リポジトリのstackを併用する場合は`aws_iam_openid_connect_provider`のリソースブロックを手動でコメントアウトするか`terraform import`すること」という注意書きに書き換えて残す
- 「apply後」セクションから`terraform output cloudwatch_dashboard_url`相当の記述があれば削除

### `SPEC.md`
- 「進捗状況」に今回の簡略化（監視リソース除外・variable削減）を1エントリとして追記し、理由（YAGNI優先・まず動くものをリリース）を記録

## 検証
- `cd infra && terraform fmt -check` と `terraform init -backend=false -input=false && terraform validate` を実行し、構文・整合性を確認する
- `grep -rn "var\.\(image_tag\|lambda_memory_size\|lambda_timeout\|reserved_concurrency\|log_retention_days\|ecr_keep_images\|github_deploy_branch\|create_github_oidc_provider\|existing_github_oidc_provider_arn\|notification_email\|duration_alarm_threshold_ms\|budget_limit_usd\)" infra/` で削除した変数への参照が残っていないことを確認
