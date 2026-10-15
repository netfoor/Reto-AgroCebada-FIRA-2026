# Bucket privado: solo CloudFront puede leerlo (control de acceso de origen, OAC).

data "aws_caller_identity" "actual" {}

resource "aws_s3_bucket" "sitio" {
  bucket        = "${var.nombre}-sitio-${data.aws_caller_identity.actual.account_id}"
  force_destroy = true # `terraform destroy` borra también los archivos publicados
}

resource "aws_s3_bucket_public_access_block" "sitio" {
  bucket                  = aws_s3_bucket.sitio.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_ownership_controls" "sitio" {
  bucket = aws_s3_bucket.sitio.id
  rule {
    object_ownership = "BucketOwnerEnforced"
  }
}

data "aws_iam_policy_document" "sitio" {
  statement {
    sid       = "LecturaDesdeCloudFront"
    actions   = ["s3:GetObject"]
    resources = ["${aws_s3_bucket.sitio.arn}/*"]
    principals {
      type        = "Service"
      identifiers = ["cloudfront.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "AWS:SourceArn"
      values   = [aws_cloudfront_distribution.sitio.arn]
    }
  }
}

resource "aws_s3_bucket_policy" "sitio" {
  bucket     = aws_s3_bucket.sitio.id
  policy     = data.aws_iam_policy_document.sitio.json
  depends_on = [aws_s3_bucket_public_access_block.sitio]
}

# Archivos del sitio. Terraform sube solo los que cambian (comparando su MD5).
# Los recursos con huella en el nombre (_astro/) se guardan un año; lo demás se revalida siempre,
# así una publicación nueva se ve sin invalidar la caché de CloudFront.
locals {
  archivos_sitio = fileset(var.carpeta_sitio, "**")
  tipos = {
    html        = "text/html; charset=utf-8"
    css         = "text/css; charset=utf-8"
    js          = "text/javascript; charset=utf-8"
    mjs         = "text/javascript; charset=utf-8"
    json        = "application/json; charset=utf-8"
    csv         = "text/csv; charset=utf-8"
    txt         = "text/plain; charset=utf-8"
    md          = "text/markdown; charset=utf-8"
    xml         = "application/xml"
    svg         = "image/svg+xml"
    png         = "image/png"
    jpg         = "image/jpeg"
    jpeg        = "image/jpeg"
    webp        = "image/webp"
    avif        = "image/avif"
    ico         = "image/x-icon"
    woff2       = "font/woff2"
    pdf         = "application/pdf"
    xlsx        = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    webmanifest = "application/manifest+json"
  }
}

resource "aws_s3_object" "sitio" {
  for_each = local.archivos_sitio

  bucket        = aws_s3_bucket.sitio.id
  key           = each.value
  source        = "${var.carpeta_sitio}/${each.value}"
  source_hash   = filemd5("${var.carpeta_sitio}/${each.value}")
  content_type  = lookup(local.tipos, lower(reverse(split(".", each.value))[0]), "application/octet-stream")
  cache_control = startswith(each.value, "_astro/") ? "public, max-age=31536000, immutable" : "no-cache"
}
