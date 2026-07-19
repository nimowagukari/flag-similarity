variable "aws_region" {
  description = "デプロイ先のAWSリージョン"
  type        = string
  default     = "ap-northeast-1"
}

variable "project_name" {
  description = "リソース名のprefix兼タグ。フォークして自分のAWSアカウントにデプロイする場合は変更を推奨（ECRリポジトリ名やLambda関数名などグローバル/アカウント内で衝突しうる名前に使われる）"
  type        = string
  default     = "flag-similarity"
}

variable "github_repository" {
  description = "GitHub Actions OIDCでのデプロイを許可する `owner/repo`。フォークした場合は自分のリポジトリに変更すること"
  type        = string
  default     = "nimowagukari/flag-similarity"
}

variable "github_oidc_provider_arn" {
  description = "既存のGitHub Actions用IAM OIDCプロバイダ(token.actions.githubusercontent.com)のARN。IAM OIDCプロバイダはAWSアカウント内で1つしか作成できないためこのTerraformでは作成せず、作成済みのものを参照する。存在しない場合は `aws iam create-open-id-connect-provider` 等で事前に作成すること（手順はREADME.md参照）"
  type        = string
}

variable "domain_name" {
  description = "API Gatewayに割り当てるカスタムドメイン名(例: quiz.example.com)。空文字の場合はカスタムドメインを作成せず、API Gatewayのデフォルトエンドポイント(execute-api)のみで公開する"
  type        = string
  default     = ""
}

variable "acm_certificate_arn" {
  description = "domain_name用の検証済みACM証明書のARN(API Gatewayと同じリージョンに発行済みのもの)。証明書の発行・DNS検証はこのTerraformの管理対象外のため、事前に用意したものを渡す。domain_nameを設定する場合は必須"
  type        = string
  default     = ""
}
