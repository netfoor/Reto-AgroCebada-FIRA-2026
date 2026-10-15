# Subdominio propio. El DNS de foor.dev está en Cloudflare, así que los registros se crean a mano:
# 1) el CNAME que valida el certificado y 2) el CNAME del subdominio hacia CloudFront (ver README).

resource "aws_acm_certificate" "dominio" {
  count             = var.dominio == null ? 0 : 1
  provider          = aws.us_east_1
  domain_name       = var.dominio
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }
}

# Espera a que ACM vea el CNAME de validación (créalo en Cloudflare mientras corre el apply).
resource "aws_acm_certificate_validation" "dominio" {
  count           = var.dominio == null ? 0 : 1
  provider        = aws.us_east_1
  certificate_arn = aws_acm_certificate.dominio[0].arn

  timeouts {
    create = "60m"
  }
}
