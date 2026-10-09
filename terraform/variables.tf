variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "Default GCP region for resources"
  type        = string
  default     = "asia-southeast1"
}