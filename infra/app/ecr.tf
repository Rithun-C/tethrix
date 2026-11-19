# Where the backend image is stored (B3-01, ADR-0004).

module "ecr" {
  source = "../modules/ecr_repository"

  name           = "${var.project}-backend"
  images_to_keep = 3 # B3 decision 6
  force_delete   = var.final_destroy
}
