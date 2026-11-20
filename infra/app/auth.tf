# Sign-in (B4-01, ADR-0003 and its 2026-11-20 update): a Cognito user pool, its hosted
# sign-in pages on Cognito's own address, and the app client the React app uses.

locals {
  # Where the app runs. The Cognito client may send users back only here (T-039).
  app_url = var.use_custom_domain ? "https://${var.domain_name}" : aws_apigatewayv2_api.app.api_endpoint

  cognito_domain_url = "https://${aws_cognito_user_pool_domain.app.domain}.auth.${var.region}.amazoncognito.com"
  cognito_issuer     = "https://cognito-idp.${var.region}.amazonaws.com/${aws_cognito_user_pool.app.id}"
}

resource "aws_cognito_user_pool" "app" {
  name = "${var.project}-users"

  # Lite: sign-in, MFA with an authenticator app, the classic hosted pages. Free for
  # 10,000 monthly users. New pools default to Essentials, so this is set on purpose
  # (SR-04, ADR-0003).
  user_pool_tier = "LITE"

  # Deleting the pool deletes every account. Off only for the final destroy (O-11).
  deletion_protection = var.final_destroy ? "INACTIVE" : "ACTIVE"

  # Sign in with the email address, in any letter case.
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]
  username_configuration {
    case_sensitive = false
  }

  # Only the admin creates accounts (I-01), with `make user-create`.
  admin_create_user_config {
    allow_admin_create_user_only = true
  }

  # An authenticator app code at every sign-in. No SMS: it costs money and is weaker
  # (SR-04, project cost rules).
  mfa_configuration = "ON"
  software_token_mfa_configuration {
    enabled = true
  }

  # Same strength as the IAM password policy (G-08).
  password_policy {
    minimum_length                   = 14
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 3
  }

  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # Cognito's built-in sender: free, a small daily limit, enough for a few users.
  email_configuration {
    email_sending_account = "COGNITO_DEFAULT"
  }
}

# The hosted sign-in pages on Cognito's own address, `<prefix>.auth.us-east-1.amazoncognito.com`.
# A custom domain such as auth.tethrix.satrix.in would make Cognito create a CloudFront
# distribution, which this account cannot have (ADR-0007). Version 1 is the classic
# hosted UI, the only option on Lite.
resource "aws_cognito_user_pool_domain" "app" {
  domain                = var.cognito_domain_prefix
  user_pool_id          = aws_cognito_user_pool.app.id
  managed_login_version = 1
}

# The React app's entry in the pool.
resource "aws_cognito_user_pool_client" "web" {
  name         = "${var.project}-web"
  user_pool_id = aws_cognito_user_pool.app.id

  # A browser cannot keep a secret; PKCE takes its place.
  generate_secret = false

  # Authorization code flow only, through the hosted pages.
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code"]
  allowed_oauth_scopes                 = ["openid", "email"]
  supported_identity_providers         = ["COGNITO"]

  # Exact addresses only (T-039). They follow the app's address, so switching the
  # custom domain on updates them in the same apply.
  callback_urls = ["${local.app_url}/auth/callback"]
  logout_urls   = ["${local.app_url}/"]

  # No password sign-in through the API: passwords are only typed on Cognito's page.
  explicit_auth_flows = ["ALLOW_REFRESH_TOKEN_AUTH"]

  # ADR-0003 decision 5, SR-05.
  access_token_validity  = 60
  id_token_validity      = 60
  refresh_token_validity = 12
  token_validity_units {
    access_token  = "minutes"
    id_token      = "minutes"
    refresh_token = "hours"
  }

  # Sign-out revokes the refresh token (SR-05).
  enable_token_revocation = true

  # "Wrong user name or password" either way, so nobody can test which emails exist.
  prevent_user_existence_errors = "ENABLED"
}
