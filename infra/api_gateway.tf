locals {
  # domain_name未設定(空文字)の場合はカスタムドメイン関連リソースを作らず、
  # API Gatewayのデフォルトエンドポイント(execute-api)のみで公開する。
  custom_domain_enabled = var.domain_name != ""
}

resource "aws_apigatewayv2_api" "app" {
  name          = var.project_name
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda" {
  api_id                 = aws_apigatewayv2_api.app.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.app.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "default" {
  api_id    = aws_apigatewayv2_api.app.id
  route_key = "$default"
  target    = "integrations/${aws_apigatewayv2_integration.lambda.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.app.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.app.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.app.execution_arn}/*/*"
}

# --- カスタムドメイン (domain_name設定時のみ) ---------------------------
# ACM証明書の発行・DNS検証、および公開後のAレコード(Alias)作成はこのTerraformの
# 管理対象外(iam.tfのGitHub OIDCプロバイダと同じ考え方)。証明書は事前に発行・
# 検証済みのものをacm_certificate_arn変数で渡す。DNS側でAliasを向ける先の値は
# outputs.tf の custom_domain_target / custom_domain_hosted_zone_id で返すので、
# それを使って別途(別stack等で)Aレコードを作成する。

resource "aws_apigatewayv2_domain_name" "app" {
  count       = local.custom_domain_enabled ? 1 : 0
  domain_name = var.domain_name

  domain_name_configuration {
    certificate_arn = var.acm_certificate_arn
    endpoint_type   = "REGIONAL"
    security_policy = "TLS_1_2"
  }
}

resource "aws_apigatewayv2_api_mapping" "app" {
  count       = local.custom_domain_enabled ? 1 : 0
  api_id      = aws_apigatewayv2_api.app.id
  domain_name = aws_apigatewayv2_domain_name.app[0].id
  stage       = aws_apigatewayv2_stage.default.id
}
