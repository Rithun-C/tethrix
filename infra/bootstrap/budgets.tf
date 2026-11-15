# Budgets email a warning when spending crosses a line. They do not stop anything.
# The real control is destroying costly resources at the end of each session.
#
# Credits are excluded on purpose. On the Free plan, credits pay for everything, so a
# budget that counts credits always reads close to 0 USD. Excluding them shows what is
# actually being used up.
#
# Format: AWS Budgets has two ways to describe what a budget counts. The old way is a
# `cost_types` block. The new way, which the console now uses, is `metrics` plus a
# `filter_expression`. We use the new way so the code matches what AWS stores and the
# plan stays clean. The filter below matches the console default: everything except
# credits and refunds.

locals {
  # The default billing view: all costs of this account.
  billing_view_arn = "arn:aws:billing::${data.aws_caller_identity.current.account_id}:billingview/primary"
}

# The budget created in the console during G-03. The import block in imports.tf hands it
# to Terraform instead of creating a second one with the same name.
resource "aws_budgets_budget" "monthly" {
  name             = "monthly-cost"
  budget_type      = "COST"
  time_unit        = "MONTHLY"
  limit_amount     = format("%.1f", var.monthly_budget_usd)
  limit_unit       = "USD"
  metrics          = ["UnblendedCost"]
  billing_view_arn = local.billing_view_arn

  filter_expression {
    not {
      dimensions {
        key    = "RECORD_TYPE"
        values = ["Credit", "Refund"]
      }
    }
  }

  # Actual spend has passed 50%, 80% and 100% of the monthly limit.
  dynamic "notification" {
    for_each = [50, 80, 100]

    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = [var.alert_email]
    }
  }

  # AWS predicts the month will end above the limit.
  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}

# Catches a forgotten resource the next day instead of days later.
# Forecast alerts are not available on daily budgets, so this has actual spend only.
resource "aws_budgets_budget" "daily" {
  name             = "daily-cost"
  budget_type      = "COST"
  time_unit        = "DAILY"
  limit_amount     = format("%.1f", var.daily_budget_usd)
  limit_unit       = "USD"
  metrics          = ["UnblendedCost"]
  billing_view_arn = local.billing_view_arn

  filter_expression {
    not {
      dimensions {
        key    = "RECORD_TYPE"
        values = ["Credit", "Refund"]
      }
    }
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }
}
