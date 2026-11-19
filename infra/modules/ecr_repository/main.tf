# A private container registry repository (ADR-0004).

resource "aws_ecr_repository" "this" {
  #checkov:skip=CKV_AWS_136:AES-256 (AWS-managed) encryption instead of a KMS key, project cost rule.
  name = var.name

  # A tag can never be moved to another image. Our tags are Git commit IDs, so a tag
  # always means the same code.
  image_tag_mutability = "IMMUTABLE"

  # Basic scanning is free and runs on every push. Trivy has already scanned the image
  # before the push; this is a second opinion from AWS.
  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  # false: destroy fails while images exist, so a typo cannot delete the images.
  # The final destroy (O-11) empties the repository first.
  force_delete = var.force_delete
}

# Keeps only the newest images. Storage is the one small recurring cost of the backend,
# and the previous image is enough for a rollback.
resource "aws_ecr_lifecycle_policy" "this" {
  repository = aws_ecr_repository.this.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep the newest ${var.images_to_keep} images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = var.images_to_keep
      }
      action = { type = "expire" }
    }]
  })
}
