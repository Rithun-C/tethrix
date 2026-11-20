# The backend: our image on Lambda with the Web Adapter (B3-02, ADR-0004).

locals {
  backend_image_uri = var.backend_image_tag == null ? null : "${module.ecr.repository_url}:${var.backend_image_tag}"
}

module "backend" {
  source = "../modules/lambda_container_api"

  name                 = "${var.project}-api"
  description          = "FastAPI backend and React app behind API Gateway (ADR-0007)."
  image_uri            = local.backend_image_uri
  memory_mb            = 512
  timeout_seconds      = 10
  reserved_concurrency = var.lambda_reserved_concurrency

  # Not secret: the browser sees all of these during sign-in. Never AUTH_MODE or
  # LOCAL_OIDC_* (make guard-local-auth, SR-06).
  environment = {
    LOG_LEVEL            = "INFO"
    DYNAMODB_TABLE       = module.table.name
    COGNITO_USER_POOL_ID = aws_cognito_user_pool.app.id
    COGNITO_CLIENT_ID    = aws_cognito_user_pool_client.web.id
    COGNITO_DOMAIN       = local.cognito_domain_url
  }

  # B4: the sign-in check reads the user's profile item, and nothing else (SR-70). B5
  # adds the todo actions and the index.
  dynamodb_actions       = ["dynamodb:GetItem"]
  dynamodb_resource_arns = [module.table.arn]
}
