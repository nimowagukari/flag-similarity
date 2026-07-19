# infra/ — Terraform (AWS Lambda + Lambda Web Adapter)

flag-similarity を AWS Lambda（コンテナイメージ + [Lambda Web Adapter](https://github.com/aws/aws-lambda-web-adapter)）+ API Gateway (HTTP API) で動かすためのTerraform一式。

背景・全体方針は [../SPEC.md](../SPEC.md) の「本番リリース計画」を参照。

## 構成

| ファイル | 内容 |
| --- | --- |
| `versions.tf` | Terraform/プロバイダバージョン、S3バックエンド宣言（値は空。initで注入） |
| `variables.tf` | `aws_region` / `project_name` / `github_repository` / `github_oidc_provider_arn` / `domain_name` / `acm_certificate_arn` のみ変数化。それ以外の設定値（メモリサイズ、Reserved Concurrencyなど）は各`.tf`にハードコード（変更したい場合はコードを直接編集する） |
| `provider.tf` | AWSプロバイダ、default_tags |
| `ecr.tf` | アプリのコンテナイメージ用ECRリポジトリ・ライフサイクルポリシー |
| `lambda.tf` | Lambda関数(container image, arm64)・ロググループ |
| `api_gateway.tf` | API Gateway (HTTP API) + Lambda統合、カスタムドメイン(`domain_name`設定時のみACM証明書・Route53レコードを作成) |
| `iam.tf` | Lambda実行ロール、GitHub Actionsデプロイロール（OIDCプロバイダ自体はこのTerraformの管理対象外。下記「前提条件」参照） |
| `outputs.tf` | API GatewayのURLなど、apply後に必要な値 |

まずは動くものをリリースすることを優先し、CloudWatch Dashboard/Alarm・SNS通知・AWS Budgetなどの監視系リソースは今回のスコープから外している（リリース後に必要になったら追加する）。

このリポジトリをフォークして自分のAWSアカウントにデプロイする場合は、`project_name` / `github_repository` / `github_oidc_provider_arn` を必ず自分の値に変更してください（ECRリポジトリ名やLambda関数名の衝突回避、OIDCの信頼範囲を自分のリポジトリに限定するため）。それ以外の値（メモリサイズ・タイムアウト・Reserved Concurrencyなど）を変えたい場合は、該当する`.tf`ファイルを直接編集する。

### カスタムドメイン

`domain_name` / `acm_certificate_arn` を設定すると、API GatewayのデフォルトURL(execute-api)に加えてカスタムドメインでの公開が有効になる。未設定（空文字のまま）の場合はexecute-apiのデフォルトURLのみで公開される。

ACM証明書の発行・DNS検証、および公開後のDNSレコード（Aレコード/Alias）作成はこのTerraformの管理対象外（`github_oidc_provider_arn`と同じ考え方で、他stackやDNS管理側の責務と分離している）。手順:

1. 使うドメインに対して、API Gatewayと同じリージョン（`ap-northeast-1`）でACM証明書をDNS検証まで済ませ、そのARNを`acm_certificate_arn`に設定する
2. `domain_name` / `acm_certificate_arn` を設定して`terraform apply`
3. `terraform output custom_domain_target` / `terraform output custom_domain_hosted_zone_id` の値を使い、DNS側（Route53等）で`domain_name`のAliasレコード（Aレコード）を作成する

## 前提条件

- state保存先のS3バケットが**作成済みで、アクセスできる**こと（バケット自体の作成はこのTerraformの管理対象外。別途用意する）
- Terraform 1.10+ の [S3ネイティブロック機能](https://developer.hashicorp.com/terraform/language/backend/s3#state-locking) (`use_lockfile`) を使うため、DynamoDBのロックテーブルは不要（SPEC.mdの当初案ではDynamoDBロックを想定していたが、Terraformのバージョンアップにより不要と判断し簡略化した）
- GitHub Actions用のIAM OIDCプロバイダ（`token.actions.githubusercontent.com`）が**作成済み**であること。IAM OIDCプロバイダはAWSアカウント内でURLごとに1つしか作成できないため、他のstack/リポジトリと衝突しないようこのTerraformでは作成せず、既存のものを`github_oidc_provider_arn`変数で参照する方式にしている。まだ存在しない場合は事前に作成する:
  ```sh
  aws iam create-open-id-connect-provider \
    --url https://token.actions.githubusercontent.com \
    --client-id-list sts.amazonaws.com \
    --thumbprint-list 1c58a3a8518e8759bf075b76b750d4f2df264fcd
  ```
  既に存在するかどうかは `aws iam list-open-id-connect-providers` で確認できる。thumbprintの値については[GitHubのドキュメント](https://docs.github.com/actions/deployment/security-hardening-your-deployments/about-security-hardening-with-openid-connect)を参照。

## セットアップ手順

```sh
cd infra

# 1. backend設定（前提条件のバケット名を反映）
cp backend.hcl.example backend.hcl
$EDITOR backend.hcl

# 2. 変数設定（project_name / github_repository / github_oidc_provider_arn 等）
cp terraform.tfvars.example terraform.tfvars
$EDITOR terraform.tfvars

# 3. init
terraform init -backend-config=backend.hcl
```

## 初回デプロイ（ECRイメージの鶏卵問題）

`aws_lambda_function` はAWS APIの制約上、参照するECRイメージが**先に存在している**必要がある。しかしそのECRリポジトリ自体はこのTerraformで作る。そのため初回のみ2段階でapplyする。

```sh
# 1. ECRリポジトリだけ先に作る
terraform apply -target=aws_ecr_repository.app

# 2. プレースホルダイメージをビルド & push（タグは lambda.tf にハードコードした "bootstrap" 固定）
REPO_URL=$(terraform output -raw ecr_repository_url)
aws ecr get-login-password --region ap-northeast-1 | docker login --username AWS --password-stdin "$REPO_URL"
docker build --platform linux/arm64 -t "$REPO_URL:bootstrap" ..
docker push "$REPO_URL:bootstrap"

# 3. 残り全部をapply
terraform apply
```

以降のイメージ更新はTerraformではなくGitHub Actions（`.github/workflows/deploy.yml`、未作成）が `aws lambda update-function-code` で行う想定（Lambda関数リソースは `lifecycle.ignore_changes = [image_uri]` によりTerraform管理対象外にしている）。

## apply後

```sh
terraform output api_endpoint                    # アプリの公開URL(execute-apiのデフォルトエンドポイント)
terraform output custom_domain_url               # カスタムドメイン設定時の公開URL(未設定ならnull)
terraform output github_actions_deploy_role_arn  # deploy.yml の role-to-assume に設定
```

## 注意事項

- **GitHub OIDCプロバイダはこのTerraformの管理対象外**: 「前提条件」節の通り、作成済みのプロバイダのARNを`github_oidc_provider_arn`変数で渡す方式にしている（AWSアカウント内で1つしか作成できないため、他stackとの衝突を避ける目的）。
- **Reserved Concurrency**: `lambda.tf`に`reserved_concurrent_executions = 5`とハードコードしている。これがアプリ全体の同時実行数上限＝コスト上限。アクセス増に応じて値を編集する。
- **監視・通知は未実装**: CloudWatch Alarm・SNS通知・AWS Budgetは今回のスコープ外。リリース後に必要になった時点で追加する。
- **カスタムドメインは任意**: `domain_name`が空文字の間はACM証明書・Route53レコードは一切作成されない。ドメイン取得後に`domain_name`/`route53_zone_id`をセットして再applyすれば有効になる。
