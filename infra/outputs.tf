output "api_endpoint" {
  description = "アプリの公開URL(API Gatewayのデフォルトエンドポイント。execute-api)"
  value       = aws_apigatewayv2_api.app.api_endpoint
}

output "custom_domain_url" {
  description = "カスタムドメイン設定時の公開URL(domain_name未設定の場合はnull)"
  value       = local.custom_domain_enabled ? "https://${var.domain_name}" : null
}

output "custom_domain_target" {
  description = "カスタムドメイン設定時、DNS側でAlias(Aレコード)を向ける先。DNSレコード自体はこのTerraformの管理対象外のため、別途この値でAliasレコードを作成する(domain_name未設定の場合はnull)"
  value       = local.custom_domain_enabled ? aws_apigatewayv2_domain_name.app[0].domain_name_configuration[0].target_domain_name : null
}

output "custom_domain_hosted_zone_id" {
  description = "custom_domain_targetのAliasレコード作成に使うHosted Zone ID(domain_name未設定の場合はnull)"
  value       = local.custom_domain_enabled ? aws_apigatewayv2_domain_name.app[0].domain_name_configuration[0].hosted_zone_id : null
}

output "ecr_repository_url" {
  description = "docker push先のECRリポジトリURL"
  value       = aws_ecr_repository.app.repository_url
}

output "github_actions_deploy_role_arn" {
  description = "GitHub ActionsのOIDCデプロイで assume するIAMロールARN(deploy.ymlのrole-to-assumeに設定)"
  value       = aws_iam_role.github_actions_deploy.arn
}
