# The backend: our image on Lambda with the Web Adapter (B3-02, ADR-0004).

locals {
  backend_image_uri = var.backend_image_tag == null ? null : "${module.ecr.repository_url}:${var.backend_image_tag}"
}

module "backend" {
  source = "../modules/lambda_container_api"

  name                 = "${var.project}-api"
  description          = "FastAPI backend behind CloudFront (ADR-0002)."
  image_uri            = local.backend_image_uri
  memory_mb            = 512
  timeout_seconds      = 10
  reserved_concurrency = var.lambda_reserved_concurrency

  environment = {
    LOG_LEVEL      = "INFO"
    DYNAMODB_TABLE = module.table.name
  }

  # B3: the code reads no data, so no database permissions yet (SR-70). B5 adds the
  # exact actions on module.table.arn and module.table.index_arns.
  dynamodb_actions       = []
  dynamodb_resource_arns = []
}
