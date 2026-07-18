output "function_url" {
  description = "アプリの公開URL(Lambda Function URL)"
  value       = aws_lambda_function_url.app.function_url
}

output "ecr_repository_url" {
  description = "docker push先のECRリポジトリURL"
  value       = aws_ecr_repository.app.repository_url
}

output "github_actions_deploy_role_arn" {
  description = "GitHub ActionsのOIDCデプロイで assume するIAMロールARN(deploy.ymlのrole-to-assumeに設定)"
  value       = aws_iam_role.github_actions_deploy.arn
}
