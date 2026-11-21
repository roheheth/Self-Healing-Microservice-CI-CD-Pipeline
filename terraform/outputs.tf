output "bucket_name" {
  value       = aws_s3_bucket.log_bucket.id
  description = "The name of the created S3 log bucket"
}

output "bucket_arn" {
  value       = aws_s3_bucket.log_bucket.arn
  description = "The ARN of the created S3 log bucket"
}
