resource "aws_cloudwatch_log_group" "lambda" {
  name              = "/aws/lambda/${var.project_name}"
  retention_in_days = 14
}

# Flask session署名用のシークレット。Lambda環境変数として渡す(app.pyのSECRET_KEY)。
resource "random_password" "flask_secret_key" {
  length  = 32
  special = false
}

resource "aws_lambda_function" "app" {
  function_name = var.project_name
  role          = aws_iam_role.lambda_exec.arn

  package_type = "Image"
  # "bootstrap"タグは初回apply用のプレースホルダ(README.md参照)。以降は
  # GitHub Actionsが実イメージで update-function-code するため、Terraformは
  # このタグの変更を追わない(下のlifecycle.ignore_changes)。
  image_uri     = "${aws_ecr_repository.app.repository_url}:bootstrap"
  architectures = ["arm64"]

  memory_size                    = 512
  timeout                        = 10
  reserved_concurrent_executions = 5

  environment {
    variables = {
      SECRET_KEY = random_password.flask_secret_key.result
    }
  }

  logging_config {
    log_format = "Text"
    log_group  = aws_cloudwatch_log_group.lambda.name
  }

  depends_on = [aws_cloudwatch_log_group.lambda]

  lifecycle {
    # デプロイはGitHub Actionsの `aws lambda update-function-code` が担うため、
    # Terraform側でimage_uriの差分を検知・上書きしないようにする。
    ignore_changes = [image_uri]
  }
}
